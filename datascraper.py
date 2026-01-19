import requests
from bs4 import BeautifulSoup
import csv
import time
import logging

class DuckDuckGoStartupScraper:
    def __init__(self):
        """Initialize the DuckDuckGo scraper for startup funding data."""
        self.base_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://duckduckgo.com/",
            "DNT": "1",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def construct_search_queries(self, startup_name=None, industry=None):
        """
        Construct targeted search queries for finding startup funding information.
        Returns a list of query strings.
        """
        base_queries = [
            "startup grants funding",
            "venture capital investors",
            "seed funding rounds",
            "startup subsidies government",
            "angel investors early stage",
            "series A funding",
            "startup incubator programs",
        ]
        
        # Add specificity if startup name or industry is provided
        queries = base_queries.copy()
        if startup_name:
            queries = [f'"{startup_name}" funding investors'] + queries
        if industry:
            industry_queries = [f"{industry} startup grants", f"{industry} venture capital"]
            queries = industry_queries + queries
            
        return queries

    def scrape_search_results(self, query, max_results=30, delay=2):
        """
        Scrape DuckDuckGo search results for a given query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to collect
            delay: Delay between requests to avoid blocking
            
        Returns:
            List of dictionaries containing result data
        """
        results = []
        params = {
            "q": query,
            "kl": "us-en",  # Region setting (US English)
        }
        
        try:
            self.logger.info(f"Searching for: {query}")
            response = self.session.get(self.base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch results: HTTP {response.status_code}")
                return results
            
            soup = BeautifulSoup(response.text, "html.parser")
            search_results = soup.select(".result")
            
            for i, result in enumerate(search_results[:max_results]):
                # Extract title and URL
                title_elem = result.select_one(".result__title .result__a")
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                raw_url = title_elem.get("href", "")
                
                # Clean URL
                if raw_url.startswith("//duckduckgo.com/y.js?"):
                    # Extract actual URL from redirect
                    import re
                    match = re.search(r"u3=([^&]+)", raw_url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                    else:
                        url = raw_url
                else:
                    url = raw_url if raw_url.startswith("http") else f"https:{raw_url}"
                
                # Extract snippet
                snippet_elem = result.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # Extract display URL
                display_elem = result.select_one(".result__url")
                display_url = display_elem.get_text(strip=True) if display_elem else ""
                
                # Identify potential funding-related content
                funding_keywords = ["funding", "investment", "grant", "subsidy", "venture", 
                                  "capital", "series", "round", "investor", "backed", "raised"]
                is_funding_related = any(keyword.lower() in (title + snippet).lower() 
                                        for keyword in funding_keywords)
                
                result_data = {
                    "query": query,
                    "rank": i + 1,
                    "title": title,
                    "url": url,
                    "display_url": display_url,
                    "snippet": snippet,
                    "is_funding_related": is_funding_related,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                results.append(result_data)
            
            self.logger.info(f"Found {len(results)} results for query: {query}")
            
            # Respectful delay to avoid blocks[citation:1]
            time.sleep(delay)
            
        except Exception as e:
            self.logger.error(f"Error scraping query '{query}': {str(e)}")
            
        return results

    def find_funding_sources(self, startup_name=None, industry=None, queries_per_topic=3):
        """
        Main method to find funding sources and investor information.
        
        Args:
            startup_name: Specific startup name (optional)
            industry: Industry or sector (optional)
            queries_per_topic: Number of results to collect per query
            
        Returns:
            List of all collected results
        """
        all_results = []
        search_queries = self.construct_search_queries(startup_name, industry)
        
        self.logger.info(f"Starting search with {len(search_queries)} queries")
        
        for query in search_queries:
            results = self.scrape_search_results(query, max_results=queries_per_topic)
            all_results.extend(results)
            
            # Additional delay between different queries
            time.sleep(1)
        
        # Filter and prioritize funding-related results
        funding_results = [r for r in all_results if r["is_funding_related"]]
        non_funding_results = [r for r in all_results if not r["is_funding_related"]]
        
        self.logger.info(f"Total results: {len(all_results)}")
        self.logger.info(f"Funding-related: {len(funding_results)}")
        self.logger.info(f"Other results: {len(non_funding_results)}")
        
        return funding_results + non_funding_results  # Funding results first

    def export_to_csv(self, results, filename="startup_funding_sources.csv"):
        """Export results to CSV file."""
        if not results:
            self.logger.warning("No results to export")
            return False
            
        try:
            fieldnames = ["query", "rank", "title", "url", "display_url", 
                         "snippet", "is_funding_related", "timestamp"]
            
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
                
            self.logger.info(f"Exported {len(results)} results to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {str(e)}")
            return False

    def analyze_funding_patterns(self, results):
        """
        Analyze results to identify patterns in funding sources.
        
        Args:
            results: List of scraped results
            
        Returns:
            Dictionary with analysis insights
        """
        if not results:
            return {}
        
        # Categorize by URL domain
        from urllib.parse import urlparse
        domains = {}
        funding_keywords_count = {}
        
        for result in results:
            # Domain analysis
            try:
                domain = urlparse(result["url"]).netloc
                domains[domain] = domains.get(domain, 0) + 1
            except:
                pass
            
            # Keyword analysis in snippets
            if result["snippet"]:
                snippet_lower = result["snippet"].lower()
                keywords = ["grant", "subsidy", "vc", "angel", "series a", 
                          "series b", "seed", "million", "billion", "funded"]
                
                for keyword in keywords:
                    if keyword in snippet_lower:
                        funding_keywords_count[keyword] = funding_keywords_count.get(keyword, 0) + 1
        
        # Get top domains
        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
        
        analysis = {
            "total_results": len(results),
            "funding_related_count": sum(1 for r in results if r["is_funding_related"]),
            "top_domains": top_domains,
            "common_keywords": sorted(funding_keywords_count.items(), key=lambda x: x[1], reverse=True),
            "unique_queries": len(set(r["query"] for r in results))
        }
        
        return analysis


# Example usage
def main():
    """Example of how to use the DuckDuckGo startup funding scraper."""
    
    # Initialize scraper
    scraper = DuckDuckGoStartupScraper()
    
    # Example 1: General startup funding sources
    print("=== Searching for general startup funding sources ===")
    general_results = scraper.find_funding_sources(
        queries_per_topic=5  # Get 5 results per query
    )
    
    # Export results
    scraper.export_to_csv(general_results, "general_startup_funding.csv")
    
    # Analyze patterns
    analysis = scraper.analyze_funding_patterns(general_results)
    print(f"\nAnalysis:")
    print(f"- Found {analysis['total_results']} total results")
    print(f"- {analysis['funding_related_count']} are funding-related")
    print(f"- Top domains: {analysis['top_domains'][:3]}")
    
    # Example 2: Specific industry focus
    print("\n=== Searching for clean energy startup funding ===")
    clean_energy_results = scraper.find_funding_sources(
        industry="clean energy",
        queries_per_topic=3
    )
    
    scraper.export_to_csv(clean_energy_results, "clean_energy_funding.csv")
    
    return general_results, clean_energy_results


if __name__ == "__main__":
    # Run the scraper
    results1, results2 = main()
    
    # Additional: To search for a specific startup
    # scraper = DuckDuckGoStartupScraper()
    # specific_results = scraper.find_funding_sources(
    #     startup_name="OpenAI",
    #     queries_per_topic=5
    # )
