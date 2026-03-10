#!/usr/bin/env python3
"""
Upwork API v2 authentication using OAuth 2.0.
"""

import json
import pickle
import base64
from pathlib import Path
from urllib.parse import urlencode, parse_qs
import requests

# Upwork OAuth 2.0 endpoints
AUTH_URL = 'https://www.upwork.com/ab/account-security/oauth2/authorize'
TOKEN_URL = 'https://www.upwork.com/api/v3/oauth2/token'

# GraphQL endpoint
GRAPHQL_URL = 'https://www.upwork.com/api/graphql/v1'

CREDENTIALS_PATH = Path('~/Desktop/Openclaw/credentials/upwork-credentials.json').expanduser()
TOKEN_PATH = Path('~/Desktop/Openclaw/credentials/upwork-token-v2.pickle').expanduser()

def load_credentials():
    """Load Upwork API credentials."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(f"Upwork credentials not found at {CREDENTIALS_PATH}")
    
    with open(CREDENTIALS_PATH) as f:
        return json.load(f)

def save_token(token):
    """Save OAuth token for reuse."""
    with open(TOKEN_PATH, 'wb') as f:
        pickle.dump(token, f)

def load_token():
    """Load existing OAuth token."""
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as f:
            return pickle.load(f)
    return None

def get_access_token():
    """Get OAuth 2.0 access token (Client Credentials flow)."""
    creds = load_credentials()
    client_id = creds['consumer_key']
    client_secret = creds['consumer_secret']
    
    # Check for existing token
    token = load_token()
    if token:
        return token['access_token']
    
    # Client Credentials flow
    auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_string}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'client_credentials'
    }
    
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    save_token(token_data)
    
    return token_data['access_token']

def search_jobs(keywords=None, category=None, limit=50):
    """Search for jobs using Upwork GraphQL API."""
    access_token = get_access_token()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Upwork-API-Version': 'v1'
    }
    
    # GraphQL query for job search
    query = """
    query SearchJobs($filter: JobSearchFilter!, $pagination: PaginationInput) {
        jobs: freelanceJobs(filter: $filter, pagination: $pagination) {
            edges {
                node {
                    id
                    title
                    description
                    createdAt
                    budget {
                        amount
                        type
                    }
                    client {
                        companyName
                        location {
                            country
                        }
                    }
                    url: canonicalUrl
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """
    
    variables = {
        "filter": {
            "query": keywords or "",
            "sort": "NEWEST"
        },
        "pagination": {
            "first": limit
        }
    }
    
    if category:
        variables["filter"]["category"] = category
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    response = requests.post(
        GRAPHQL_URL,
        json=payload,
        headers=headers
    )
    
    response.raise_for_status()
    data = response.json()
    
    if 'errors' in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    jobs = []
    edges = data.get('data', {}).get('jobs', {}).get('edges', [])
    
    for edge in edges:
        node = edge['node']
        jobs.append({
            'id': node['id'],
            'title': node['title'],
            'description': node['description'],
            'url': f"https://www.upwork.com{node['url']}" if node['url'].startswith('/') else node['url'],
            'budget': node.get('budget'),
            'client': node.get('client'),
            'created_at': node['createdAt']
        })
    
    return jobs

if __name__ == '__main__':
    # Test the API
    print("Testing Upwork API v2 connection...")
    try:
        jobs = search_jobs(keywords="fractional CMO", limit=5)
        print(f"\nFound {len(jobs)} jobs:")
        for job in jobs:
            print(f"- {job['title'][:60]}... ({job['url']})")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
