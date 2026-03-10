#!/usr/bin/env python3
"""
The Bouncer - Policy Enforcement Agent
Enforces CSO security policies by intercepting and blocking dangerous operations.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auto_logger import log_action, log_tool_call

# Security configuration
SECURITY_DIR = Path("memory/security")
CONFIG_FILE = SECURITY_DIR / "cso-config.json"
BLOCKED_LOG = SECURITY_DIR / "blocked-operations.json"

# Allowed paths (workspace only)
ALLOWED_ROOT = Path("/Users/jcore/Desktop/Openclaw").resolve()

# High-risk operations requiring approval
HIGH_RISK_PATTERNS = {
    'file_delete_system': r'^/usr|^/bin|^/sbin|^/etc|^/var|^/System',
    'file_write_outside': r'\.\./|~\/|\$HOME|/tmp/|/var/tmp/',
    'network_suspicious': r'\.onion|\.tor|pastebin|ghostbin|termbin',
    'code_exec': r'eval\(|exec\(|compile\(|__import__',
    'privilege_escalation': r'sudo|su -|chmod.*777|chown.*root',
}

# Whitelist for specific operations
WHITELISTED_PATHS = [
    '/Users/jcore/Desktop/Openclaw',
    '/Users/jcore/Desktop/Openclaw/memory',
    '/Users/jcore/Desktop/Openclaw/outputs',
    '/Users/jcore/Desktop/Openclaw/tools',
]


class Bouncer:
    """The Bouncer - enforces security policies."""
    
    def __init__(self):
        self.config = self._load_config()
        self.blocked_count = 0
        
    def _load_config(self) -> Dict:
        """Load CSO configuration."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _log_blocked(self, operation: str, reason: str, details: Dict):
        """Log a blocked operation."""
        blocked_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'reason': reason,
            'details': details
        }
        
        # Load existing
        blocked = []
        if BLOCKED_LOG.exists():
            with open(BLOCKED_LOG, 'r') as f:
                blocked = json.load(f)
        
        blocked.append(blocked_entry)
        
        # Keep last 1000
        blocked = blocked[-1000:]
        
        with open(BLOCKED_LOG, 'w') as f:
            json.dump(blocked, f, indent=2)
        
        # Log to database
        log_action(
            action_type='blocked_operation',
            tool_name='Bouncer',
            input_params={'operation': operation, 'reason': reason},
            output_result='BLOCKED',
            success=False,  # Blocked = not successful
            metadata={'details': details}
        )
        
        self.blocked_count += 1
    
    def check_file_read(self, filepath: str) -> tuple[bool, str]:
        """Check if file read is allowed."""
        path = Path(filepath).resolve()
        
        # Check if within allowed root
        try:
            path.relative_to(ALLOWED_ROOT)
            return True, "OK"
        except ValueError:
            # Outside workspace
            self._log_blocked('file_read', 'Outside workspace', {'path': str(path)})
            return False, f"Access denied: {path} is outside workspace"
    
    def check_file_write(self, filepath: str, content: str = None) -> tuple[bool, str]:
        """Check if file write is allowed."""
        path = Path(filepath).resolve()
        
        # Check if within allowed root
        try:
            path.relative_to(ALLOWED_ROOT)
        except ValueError:
            self._log_blocked('file_write', 'Outside workspace', {'path': str(path)})
            return False, f"Write denied: {path} is outside workspace"
        
        # Check for suspicious patterns in content
        if content:
            for pattern_name, pattern in HIGH_RISK_PATTERNS.items():
                if re.search(pattern, content, re.IGNORECASE):
                    self._log_blocked('file_write', f'Suspicious content: {pattern_name}', 
                                    {'path': str(path), 'pattern': pattern_name})
                    return False, f"Write denied: Suspicious content detected ({pattern_name})"
        
        # Check if trying to overwrite sensitive files
        sensitive_files = ['.env', 'credentials/', 'memory/gerald_logs.db', 'SECURITY.md']
        for sensitive in sensitive_files:
            if sensitive in str(path):
                # Log but allow (CSO will monitor)
                log_action(
                    action_type='sensitive_file_write',
                    tool_name='Bouncer',
                    input_params={'path': str(path)},
                    output_result='ALLOWED_WITH_MONITORING',
                    success=True
                )
        
        return True, "OK"
    
    def check_file_delete(self, filepath: str) -> tuple[bool, str]:
        """Check if file deletion is allowed."""
        path = Path(filepath).resolve()
        
        # Check if within allowed root
        try:
            path.relative_to(ALLOWED_ROOT)
        except ValueError:
            self._log_blocked('file_delete', 'Outside workspace', {'path': str(path)})
            return False, f"Delete denied: {path} is outside workspace"
        
        # Check for sensitive files
        sensitive_patterns = ['.env', 'credentials/', 'memory/', 'SECURITY.md', 'BOOTSTRAP.md']
        for pattern in sensitive_patterns:
            if pattern in str(path):
                self._log_blocked('file_delete', 'Protected file', {'path': str(path)})
                return False, f"Delete denied: {path} is protected"
        
        return True, "OK"
    
    def check_shell_command(self, command: str) -> tuple[bool, str]:
        """Check if shell command is allowed."""
        # Check for high-risk patterns
        dangerous_patterns = {
            r'\brm\s+-rf\s+/': 'Recursive delete of system',
            r'sudo\s+': 'Privilege escalation',
            r'curl\s+.*\|\s*bash': 'Pipe from curl to bash',
            r'wget\s+.*\|\s*sh': 'Pipe from wget to shell',
            r'eval\s*\(': 'Code evaluation',
            r'exec\s*\(': 'Code execution',
            r'base64\s+.*\|\s*bash': 'Base64 decode to shell',
        }
        
        for pattern, reason in dangerous_patterns.items():
            if re.search(pattern, command, re.IGNORECASE):
                self._log_blocked('shell_command', reason, {'command': command[:100]})
                return False, f"Command blocked: {reason}"
        
        # Check for network calls
        if re.search(r'curl|wget|fetch', command, re.IGNORECASE):
            # Extract URLs
            urls = re.findall(r'https?://[^\s\'"]+', command)
            for url in urls:
                if self._is_blocked_domain(url):
                    self._log_blocked('shell_command', 'Blocked domain', {'url': url})
                    return False, f"Command blocked: URL {url} is blacklisted"
        
        return True, "OK"
    
    def check_network_request(self, url: str) -> tuple[bool, str]:
        """Check if network request is allowed."""
        # Check blocked domains
        if self._is_blocked_domain(url):
            self._log_blocked('network_request', 'Blocked domain', {'url': url})
            return False, f"Request blocked: Domain is blacklisted"
        
        # Check for suspicious patterns
        suspicious = ['.onion', '.tor', 'pastebin.com', 'ghostbin.co']
        for pattern in suspicious:
            if pattern in url.lower():
                self._log_blocked('network_request', 'Suspicious domain', {'url': url})
                return False, f"Request blocked: Suspicious domain pattern"
        
        return True, "OK"
    
    def check_skill_install(self, skill_name: str, skill_path: Path) -> tuple[bool, str, List[str]]:
        """
        Comprehensive skill installation check.
        Returns: (allowed, reason, warnings)
        """
        warnings = []
        
        # Check blacklist
        blacklist = self.config.get('blacklisted_skills', [])
        if skill_name in blacklist:
            self._log_blocked('skill_install', 'Blacklisted skill', {'skill': skill_name})
            return False, f"Skill '{skill_name}' is blacklisted", warnings
        
        # Check if skill directory exists
        if not skill_path.exists():
            return False, f"Skill path not found: {skill_path}", warnings
        
        # Scan all files in skill
        for file_path in skill_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Check file extension
            if file_path.suffix in ['.py', '.sh', '.js', '.rb']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Check for suspicious patterns
                    suspicious_patterns = {
                        'eval(': 'Dynamic code evaluation',
                        'exec(': 'Code execution',
                        '__import__("os").system': 'System command execution',
                        'subprocess.call': 'Subprocess execution',
                        'subprocess.run': 'Subprocess execution',
                        'os.system': 'System command',
                        'base64.b64decode': 'Base64 decoding (potential obfuscation)',
                        'requests.post': 'HTTP POST request',
                        'urllib.request': 'Network request',
                        'socket.': 'Network socket',
                    }
                    
                    for pattern, description in suspicious_patterns.items():
                        if pattern in content:
                            warnings.append(f"{file_path.name}: {description}")
                    
                    # Check for hardcoded credentials
                    if re.search(r'(password|api_key|token)\s*=\s*[\'"][^\'"]+[\'"]', content, re.IGNORECASE):
                        warnings.append(f"{file_path.name}: Possible hardcoded credentials")
                    
                except Exception as e:
                    warnings.append(f"{file_path.name}: Could not scan ({e})")
        
        # Determine risk level
        if len(warnings) > 5:
            self._log_blocked('skill_install', 'Too many security warnings', 
                            {'skill': skill_name, 'warnings': len(warnings)})
            return False, f"Skill '{skill_name}' has {len(warnings)} security concerns", warnings
        elif len(warnings) > 0:
            return True, f"Skill '{skill_name}' has warnings - requires review", warnings
        
        return True, "OK", warnings
    
    def _is_blocked_domain(self, url: str) -> bool:
        """Check if domain is in blocklist."""
        blocked = self.config.get('blocked_domains', [])
        url_lower = url.lower()
        for domain in blocked:
            if domain in url_lower:
                return True
        return False
    
    def get_stats(self) -> Dict:
        """Get bouncer statistics."""
        blocked = []
        if BLOCKED_LOG.exists():
            with open(BLOCKED_LOG, 'r') as f:
                blocked = json.load(f)
        
        # Count by operation type
        by_type = {}
        for entry in blocked:
            op = entry['operation']
            by_type[op] = by_type.get(op, 0) + 1
        
        return {
            'total_blocked': len(blocked),
            'blocked_by_type': by_type,
            'recent_blocks': blocked[-5:] if blocked else []
        }


# Singleton instance
_bouncer_instance = None

def get_bouncer() -> Bouncer:
    """Get the singleton Bouncer instance."""
    global _bouncer_instance
    if _bouncer_instance is None:
        _bouncer_instance = Bouncer()
    return _bouncer_instance


# Convenience functions for direct use
def check_file_read(filepath: str) -> tuple[bool, str]:
    """Check if file read is allowed."""
    return get_bouncer().check_file_read(filepath)

def check_file_write(filepath: str, content: str = None) -> tuple[bool, str]:
    """Check if file write is allowed."""
    return get_bouncer().check_file_write(filepath, content)

def check_file_delete(filepath: str) -> tuple[bool, str]:
    """Check if file delete is allowed."""
    return get_bouncer().check_file_delete(filepath)

def check_shell_command(command: str) -> tuple[bool, str]:
    """Check if shell command is allowed."""
    return get_bouncer().check_shell_command(command)

def check_network_request(url: str) -> tuple[bool, str]:
    """Check if network request is allowed."""
    return get_bouncer().check_network_request(url)

def check_skill_install(skill_name: str, skill_path: Path) -> tuple[bool, str, List[str]]:
    """Check if skill installation is allowed."""
    return get_bouncer().check_skill_install(skill_name, skill_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='The Bouncer - Policy Enforcement')
    parser.add_argument('--stats', action='store_true', help='Show blocked operations stats')
    parser.add_argument('--test-read', help='Test file read check')
    parser.add_argument('--test-write', help='Test file write check')
    parser.add_argument('--test-command', help='Test shell command check')
    
    args = parser.parse_args()
    
    bouncer = get_bouncer()
    
    if args.stats:
        stats = bouncer.get_stats()
        print(f"\n🥊 Bouncer Statistics")
        print(f"====================")
        print(f"Total blocked: {stats['total_blocked']}")
        print(f"\nBy operation type:")
        for op_type, count in stats['blocked_by_type'].items():
            print(f"  {op_type}: {count}")
        print()
    
    elif args.test_read:
        allowed, reason = bouncer.check_file_read(args.test_read)
        print(f"Read check: {args.test_read}")
        print(f"  Allowed: {allowed}")
        print(f"  Reason: {reason}")
    
    elif args.test_write:
        allowed, reason = bouncer.check_file_write(args.test_write)
        print(f"Write check: {args.test_write}")
        print(f"  Allowed: {allowed}")
        print(f"  Reason: {reason}")
    
    elif args.test_command:
        allowed, reason = bouncer.check_shell_command(args.test_command)
        print(f"Command check: {args.test_command}")
        print(f"  Allowed: {allowed}")
        print(f"  Reason: {reason}")
    
    else:
        parser.print_help()
