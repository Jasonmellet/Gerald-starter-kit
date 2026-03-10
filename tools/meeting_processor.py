"""
Meeting Processor for OpenClaw
Analyzes transcripts to extract customer mentions, classify topics, and generate summaries.
"""

import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class MeetingProcessor:
    """Process meeting transcripts to extract insights."""
    
    def __init__(self):
        """Initialize the processor."""
        self.customer_patterns = [
            # Common patterns for customer mentions
            r'(?:customer|client)\s+(\w+(?:\s+\w+)?)',
            r'(?:with|for)\s+(\w+(?:\s+\w+)?)\s+(?:customer|client)',
            r'(\w+(?:\s+\w+)?)\s+(?:account|project|engagement)',
        ]
    
    def process_transcript(
        self,
        transcript: List[Dict[str, Any]],
        meeting_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a full transcript and extract structured information.
        
        Args:
            transcript: List of transcript segments from Recall.ai
            meeting_info: Dict with meeting metadata (subject, date, etc.)
            
        Returns:
            Structured analysis of the meeting
        """
        # Combine transcript into full text
        full_text = self._combine_transcript(transcript)
        
        # Extract customer mentions
        customers = self._extract_customers(full_text, transcript)
        
        # Extract action items
        action_items = self._extract_action_items(full_text, transcript)
        
        # Generate summary per customer
        customer_summaries = self._summarize_by_customer(
            customers, full_text, transcript
        )
        
        # Extract key topics/themes
        topics = self._extract_topics(full_text)
        
        return {
            'meeting_info': meeting_info,
            'processed_at': datetime.now().isoformat(),
            'summary': {
                'total_segments': len(transcript),
                'customers_discussed': list(customers.keys()),
                'action_items_count': len(action_items),
                'key_topics': topics
            },
            'customers': customer_summaries,
            'action_items': action_items,
            'full_transcript': transcript,
            'raw_text': full_text
        }
    
    def _combine_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """Combine transcript segments into readable text."""
        lines = []
        for segment in transcript:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '')
            lines.append(f"{speaker}: {text}")
        return '\n'.join(lines)
    
    def _extract_customers(
        self,
        full_text: str,
        transcript: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict]]:
        """
        Extract customer mentions from transcript.
        
        Returns:
            Dict mapping customer name to list of mentions with context
        """
        customers = {}
        
        # Pattern-based extraction
        for pattern in self.customer_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                customer_name = match.group(1).strip()
                if len(customer_name) > 2:  # Filter out short matches
                    if customer_name not in customers:
                        customers[customer_name] = []
                    
                    # Get context around mention
                    start = max(0, match.start() - 100)
                    end = min(len(full_text), match.end() + 100)
                    context = full_text[start:end]
                    
                    customers[customer_name].append({
                        'context': context,
                        'position': match.start(),
                        'extracted_by': 'pattern'
                    })
        
        # Look for capitalized names that might be companies
        # Simple heuristic: look for "at CompanyName" or "from CompanyName"
        company_patterns = [
            r'(?:at|from|with)\s+([A-Z][\w\s&]+?)(?:\s+(?:today|yesterday|last|this)|\.|,|\n|$)',
            r'(?:company|organization)\s+(?:called|named)?\s+([A-Z][\w\s&]+)',
        ]
        
        for pattern in company_patterns:
            matches = re.finditer(pattern, full_text)
            for match in matches:
                company = match.group(1).strip()
                if company and company not in customers:
                    customers[company] = [{
                        'context': match.group(0),
                        'position': match.start(),
                        'extracted_by': 'company_pattern'
                    }]
        
        return customers
    
    def _extract_action_items(
        self,
        full_text: str,
        transcript: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract action items and tasks from transcript."""
        action_items = []
        
        # Keywords that indicate action items
        action_keywords = [
            'action item', 'follow up', 'follow-up', 'to do', 'todo',
            'need to', 'should', 'will', 'going to', 'plan to',
            'by next', 'by tomorrow', 'by Friday', 'by Monday'
        ]
        
        # Split by speaker turns
        for segment in transcript:
            text = segment.get('text', '').lower()
            speaker = segment.get('speaker', 'Unknown')
            
            for keyword in action_keywords:
                if keyword in text:
                    # Extract the sentence containing the action
                    sentences = re.split(r'[.!?]+', text)
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            action_items.append({
                                'text': sentence.strip(),
                                'speaker': speaker,
                                'keyword': keyword,
                                'timestamp': segment.get('timestamp')
                            })
                            break
        
        # Deduplicate similar items
        unique_items = []
        seen_texts = set()
        for item in action_items:
            # Normalize text for deduplication
            normalized = re.sub(r'\s+', ' ', item['text'].lower().strip())
            if normalized not in seen_texts and len(normalized) > 10:
                seen_texts.add(normalized)
                unique_items.append(item)
        
        return unique_items
    
    def _summarize_by_customer(
        self,
        customers: Dict[str, List],
        full_text: str,
        transcript: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """Generate summary for each customer mentioned."""
        summaries = {}
        
        for customer_name, mentions in customers.items():
            # Collect all segments mentioning this customer
            relevant_segments = []
            customer_lower = customer_name.lower()
            
            for segment in transcript:
                text = segment.get('text', '')
                if customer_lower in text.lower():
                    relevant_segments.append(segment)
            
            # Extract key points (sentences mentioning customer)
            key_points = []
            for mention in mentions:
                context = mention.get('context', '')
                # Split context into sentences
                sentences = re.split(r'[.!?]+', context)
                for sentence in sentences:
                    if customer_lower in sentence.lower() and len(sentence) > 20:
                        key_points.append(sentence.strip())
            
            # Remove duplicates while preserving order
            seen = set()
            unique_points = []
            for point in key_points:
                normalized = re.sub(r'\s+', ' ', point.lower())
                if normalized not in seen:
                    seen.add(normalized)
                    unique_points.append(point)
            
            summaries[customer_name] = {
                'mention_count': len(mentions),
                'key_points': unique_points[:5],  # Top 5 points
                'relevant_segments_count': len(relevant_segments),
                'first_mention_position': mentions[0].get('position') if mentions else None
            }
        
        return summaries
    
    def _extract_topics(self, full_text: str) -> List[str]:
        """Extract key topics/themes discussed."""
        topics = []
        
        # Common business topics to look for
        topic_keywords = {
            'pricing': ['price', 'cost', 'budget', 'quote', 'proposal'],
            'timeline': ['timeline', 'schedule', 'deadline', 'milestone', 'delivery'],
            'technical': ['technical', 'integration', 'api', 'implementation', 'architecture'],
            'requirements': ['requirement', 'feature', 'functionality', 'spec'],
            'concerns': ['concern', 'issue', 'problem', 'risk', 'challenge'],
            'next_steps': ['next step', 'moving forward', 'follow up', 'schedule']
        }
        
        text_lower = full_text.lower()
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    topics.append(topic)
                    break
        
        return list(set(topics))  # Remove duplicates
    
    def save_analysis(
        self,
        analysis: Dict[str, Any],
        output_dir: str = "memory/meetings"
    ) -> str:
        """
        Save analysis to disk.
        
        Args:
            analysis: The processed meeting analysis
            output_dir: Directory to save files
            
        Returns:
            Path to saved file
        """
        # Create directory if needed
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate filename from meeting info
        meeting_info = analysis.get('meeting_info', {})
        date_str = meeting_info.get('date', datetime.now().strftime('%Y-%m-%d'))
        subject = meeting_info.get('subject', 'meeting')
        # Clean subject for filename
        subject_clean = re.sub(r'[^\w\-]', '_', subject)[:50]
        
        filename = f"{date_str}_{subject_clean}_analysis.json"
        filepath = Path(output_dir) / filename
        
        # Save as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Also save a markdown summary
        md_filename = f"{date_str}_{subject_clean}_summary.md"
        md_filepath = Path(output_dir) / md_filename
        self._save_markdown_summary(analysis, md_filepath)
        
        return str(filepath)
    
    def _save_markdown_summary(self, analysis: Dict[str, Any], filepath: Path):
        """Save a human-readable markdown summary."""
        meeting_info = analysis.get('meeting_info', {})
        summary = analysis.get('summary', {})
        customers = analysis.get('customers', {})
        action_items = analysis.get('action_items', [])
        
        lines = [
            f"# Meeting Summary: {meeting_info.get('subject', 'Unknown')}",
            "",
            f"**Date:** {meeting_info.get('date', 'Unknown')}",
            f"**Processed:** {analysis.get('processed_at', 'Unknown')}",
            "",
            "## Overview",
            "",
            f"- **Customers Discussed:** {len(summary.get('customers_discussed', []))}",
            f"- **Action Items:** {summary.get('action_items_count', 0)}",
            f"- **Key Topics:** {', '.join(summary.get('key_topics', []))}",
            "",
            "## Customers",
            ""
        ]
        
        for customer_name, customer_data in customers.items():
            lines.extend([
                f"### {customer_name}",
                "",
                f"**Mentions:** {customer_data.get('mention_count', 0)}",
                "",
                "**Key Points:**",
                ""
            ])
            
            for point in customer_data.get('key_points', []):
                lines.append(f"- {point}")
            
            lines.append("")
        
        lines.extend([
            "## Action Items",
            ""
        ])
        
        for item in action_items:
            speaker = item.get('speaker', 'Unknown')
            text = item.get('text', '')
            lines.append(f"- [{speaker}] {text}")
        
        lines.append("")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


if __name__ == "__main__":
    # Test with sample data
    print("MeetingProcessor loaded successfully")
