#!/usr/bin/env python3
"""
Knowledge Base Ingestion System for Model Realignment
Builds vector database from OpenAI docs and grey literature
"""

import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
import time
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer


class KnowledgeBaseIngester:
    """
    Ingests knowledge from various sources and creates a vector database
    for the veracity module to query
    """
    
    def __init__(self, db_path: str = "data/chroma_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="ai_capabilities_knowledge",
            metadata={"description": "Knowledge about AI capabilities for lie detection"}
        )
        
        # Sources to scrape
        self.official_sources = [
            "https://platform.openai.com/docs/models",
            "https://platform.openai.com/docs/guides/text-generation", 
            "https://platform.openai.com/docs/api-reference/chat",
            "https://platform.openai.com/docs/guides/function-calling",
            "https://platform.openai.com/docs/guides/vision",
            "https://openai.com/api/pricing/"
        ]
        
        # Grey literature search terms for Brave Search
        self.grey_search_terms = [
            "ChatGPT system prompt reverse engineering",
            "OpenAI API hidden capabilities",
            "GPT-4 jailbreak techniques",
            "ChatGPT can't do limitations false", 
            "OpenAI model capabilities documentation",
            "GPT real capabilities vs claimed limitations",
            "ChatGPT internet access capability",
            "OpenAI function calling examples"
        ]
    
    def ingest_all_sources(self) -> Dict[str, Any]:
        """
        Ingest knowledge from all configured sources
        
        Returns:
            Summary of ingestion results
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "official_docs": {},
            "grey_literature": {},
            "total_chunks": 0,
            "errors": []
        }
        
        self.logger.info("Starting knowledge base ingestion")
        
        # Ingest official OpenAI documentation
        for url in self.official_sources:
            try:
                chunk_count = self.ingest_official_docs(url)
                results["official_docs"][url] = chunk_count
                results["total_chunks"] += chunk_count
                self.logger.info(f"Ingested {chunk_count} chunks from {url}")
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                error_msg = f"Failed to ingest {url}: {str(e)}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
        
        # Ingest grey literature via Brave Search
        if os.getenv("BRAVE_API_KEY"):
            for search_term in self.grey_search_terms:
                try:
                    chunk_count = self.ingest_grey_literature(search_term)
                    results["grey_literature"][search_term] = chunk_count
                    results["total_chunks"] += chunk_count
                    self.logger.info(f"Ingested {chunk_count} chunks for '{search_term}'")
                    time.sleep(2)  # More conservative rate limiting
                    
                except Exception as e:
                    error_msg = f"Failed to search '{search_term}': {str(e)}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)
        else:
            results["errors"].append("BRAVE_API_KEY not set - skipping grey literature")
        
        # Save ingestion metadata
        self.save_ingestion_metadata(results)
        
        self.logger.info(f"Ingestion completed: {results['total_chunks']} total chunks")
        return results
    
    def ingest_official_docs(self, url: str) -> int:
        """
        Scrape and ingest official OpenAI documentation
        
        Args:
            url: URL to scrape
            
        Returns:
            Number of chunks created
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content (remove navigation, ads, etc.)
        content = ""
        
        # Try common content selectors
        content_selectors = [
            'main', 'article', '.content', '#content',
            '.documentation', '.docs-content', '.markdown-body'
        ]
        
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(separator='\n', strip=True)
                break
        
        if not content:
            # Fallback: get all text
            content = soup.get_text(separator='\n', strip=True)
        
        return self.process_and_store_content(
            content=content,
            source_url=url,
            source_type="official_docs",
            title=soup.title.string if soup.title else url
        )
    
    def ingest_grey_literature(self, search_term: str) -> int:
        """
        Search and ingest grey literature using Brave Search API
        
        Args:
            search_term: Search query
            
        Returns:
            Number of chunks created
        """
        brave_api_key = os.getenv("BRAVE_API_KEY")
        if not brave_api_key:
            raise ValueError("BRAVE_API_KEY environment variable not set")
        
        # Search using Brave API
        search_url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": brave_api_key
        }
        
        params = {
            "q": search_term,
            "count": 10,  # Top 10 results
            "safesearch": "moderate",
            "text_decorations": False
        }
        
        response = requests.get(search_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        search_results = response.json()
        
        total_chunks = 0
        
        # Process each search result
        for result in search_results.get("web", {}).get("results", [])[:5]:  # Limit to top 5
            try:
                url = result.get("url", "")
                title = result.get("title", "")
                description = result.get("description", "")
                
                # Skip certain domains
                skip_domains = ["youtube.com", "reddit.com/r/", "twitter.com", "facebook.com"]
                if any(domain in url.lower() for domain in skip_domains):
                    continue
                
                # Try to fetch the full content
                content = self.fetch_webpage_content(url)
                if content:
                    # Combine title, description, and content
                    full_content = f"Title: {title}\nDescription: {description}\n\nContent:\n{content}"
                    
                    chunks = self.process_and_store_content(
                        content=full_content,
                        source_url=url,
                        source_type="grey_literature",
                        title=title,
                        search_term=search_term
                    )
                    
                    total_chunks += chunks
                    time.sleep(1)  # Rate limiting between pages
                
            except Exception as e:
                self.logger.warning(f"Failed to process {result.get('url', 'unknown')}: {e}")
                continue
        
        return total_chunks
    
    def fetch_webpage_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract text content from a webpage
        
        Args:
            url: URL to fetch
            
        Returns:
            Extracted text content or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            content = soup.get_text(separator='\n', strip=True)
            
            # Basic content validation
            if len(content) < 500:  # Too short
                return None
                
            if len(content) > 50000:  # Too long, truncate
                content = content[:50000]
            
            return content
            
        except Exception as e:
            self.logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    def process_and_store_content(
        self, 
        content: str, 
        source_url: str, 
        source_type: str, 
        title: str = "",
        search_term: str = ""
    ) -> int:
        """
        Process content into chunks and store in vector database
        
        Args:
            content: Raw text content
            source_url: Source URL
            source_type: Type of source (official_docs, grey_literature)
            title: Document title
            search_term: Search term used (for grey literature)
            
        Returns:
            Number of chunks created
        """
        if not content or len(content.strip()) < 100:
            return 0
        
        # Split content into chunks
        chunks = self.text_splitter.split_text(content)
        
        if not chunks:
            return 0
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Create document IDs and metadata
        ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID
            chunk_id = hashlib.md5(f"{source_url}_{i}_{chunk[:100]}".encode()).hexdigest()
            ids.append(chunk_id)
            
            # Create metadata
            metadata = {
                "source_url": source_url,
                "source_type": source_type,
                "title": title[:200],  # Limit title length
                "chunk_index": i,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(chunk)
            }
            
            if search_term:
                metadata["search_term"] = search_term
            
            metadatas.append(metadata)
        
        # Store in ChromaDB
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(chunks)
    
    def query_knowledge_base(
        self, 
        query: str, 
        n_results: int = 10,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the knowledge base for relevant information
        
        Args:
            query: Search query
            n_results: Number of results to return
            source_type: Filter by source type (optional)
            
        Returns:
            List of relevant documents with metadata
        """
        where_filter = {}
        if source_type:
            where_filter["source_type"] = source_type
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i]
            })
        
        return formatted_results
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge database"""
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze source distribution
            sample = self.collection.get(limit=min(count, 1000))
            
            source_types = {}
            source_urls = {}
            
            for metadata in sample['metadatas']:
                source_type = metadata.get('source_type', 'unknown')
                source_url = metadata.get('source_url', 'unknown')
                
                source_types[source_type] = source_types.get(source_type, 0) + 1
                source_urls[source_url] = source_urls.get(source_url, 0) + 1
            
            return {
                "total_documents": count,
                "source_types": source_types,
                "unique_sources": len(source_urls),
                "top_sources": sorted(source_urls.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}
    
    def save_ingestion_metadata(self, results: Dict[str, Any]) -> None:
        """Save ingestion results to metadata file"""
        metadata_file = self.db_path / "ingestion_metadata.json"
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save ingestion metadata: {e}")


def main():
    """Main entry point for knowledge ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Realignment Knowledge Ingestion")
    parser.add_argument("--ingest", action="store_true", help="Run full ingestion")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--query", type=str, help="Query the knowledge base")
    parser.add_argument("--official-only", action="store_true", help="Ingest only official docs")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    ingester = KnowledgeBaseIngester()
    
    if args.ingest:
        if args.official_only:
            results = {"official_docs": {}, "total_chunks": 0, "errors": []}
            for url in ingester.official_sources:
                try:
                    chunk_count = ingester.ingest_official_docs(url)
                    results["official_docs"][url] = chunk_count
                    results["total_chunks"] += chunk_count
                    time.sleep(1)
                except Exception as e:
                    results["errors"].append(f"Failed to ingest {url}: {str(e)}")
        else:
            results = ingester.ingest_all_sources()
        
        print(json.dumps(results, indent=2))
    
    elif args.stats:
        stats = ingester.get_database_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.query:
        results = ingester.query_knowledge_base(args.query)
        print(f"\nQuery: {args.query}")
        print(f"Found {len(results)} results:\n")
        
        for i, result in enumerate(results[:5], 1):
            print(f"{i}. [{result['metadata']['source_type']}] {result['metadata']['title']}")
            print(f"   Distance: {result['distance']:.3f}")
            print(f"   URL: {result['metadata']['source_url']}")
            print(f"   Content: {result['content'][:200]}...")
            print()
    
    else:
        print("Use --ingest to build knowledge base, --stats to view statistics, or --query 'text' to search")


if __name__ == "__main__":
    main()