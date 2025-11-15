import httpx
import json
import time
from pathlib import Path

# County OSM relation IDs
COUNTIES = {
    "alameda": "3600396499",
    "contra_costa": "3600396462",
    "san_francisco": "3600111968",
    "san_mateo": "3600396498",
    "santa_clara": "3600396501"
}

# Query tags by category
QUERIES = {
    "religion": [
        "amenity=place_of_worship",
        "building=temple",
        "building=synagogue",
        "building=mosque",
        "building=church",
        "building=cathedral",
        "building=chapel",
        "building=gurdwara",
        "religion",
        "denomination"
    ],
    "social_community": [
        "amenity=social_facility",
        "amenity=arts_centre",
        "amenity=community_centre"
    ],
    "events": [
        "amenity=theatre",
        "amenity=nightclub",
        "amenity=events_venue",
        "amenity=conference_centre",
        "leisure=stadium",
        "amenity=marketplace",
        "amenity=exhibition_centre",
        "amenity=festival_grounds",
        "leisure=festival_grounds"
    ],
    "bikeshops": [
        "shop=bicycle"
    ],
    "bookstores": [
        "shop=books"
    ]
}

def build_overpass_query(relation_id, tags):
    """Build Overpass API query string for area union of tags."""
    area_part = f"area({relation_id})->.searchArea;"
    tag_parts = "\n  ".join([f"nwr[{tag}](area.searchArea);" for tag in tags])
    query = f"[out:json];\n{area_part}\n(\n  {tag_parts}\n);\nout meta;"
    return query

def query_overpass(query_str, max_retries=5):
    """Execute Overpass query with retry logic and exponential backoff."""
    url = "https://overpass-api.de/api/interpreter"

    for attempt in range(max_retries):
        try:
            print(f"Making request (attempt {attempt + 1}/{max_retries})...")
            response = httpx.post(url, data=query_str, timeout=60)

            if response.status_code == 200:
                return response.json()
            elif response.status_code >= 500 or response.status_code == 429:
                # Server error or rate limit, retry
                delay = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                print(f"Server/rate limit error {response.status_code}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                # Other client error, don't retry
                print(f"Client error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            delay = 2 ** attempt if attempt < max_retries - 1 else 0
            print(f"Request failed: {e}")
            if delay > 0:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                break

    print("Max retries exceeded")
    return None

def main():
    """Query OSM data for all counties and categories, save to JSON files."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"Output directory: {data_dir.absolute()}")

    total_queries = len(COUNTIES) * len(QUERIES)
    completed = 0

    for county, relation_id in COUNTIES.items():
        for category, tags in QUERIES.items():
            print(f"\n[{completed + 1}/{total_queries}] Querying {county} {category}...")

            # Build query
            query_str = build_overpass_query(relation_id, tags)
            print(f"Query has {len(tags)} tag conditions")

            # Check if file already exists in subdir
            county_dir = data_dir / county
            county_dir.mkdir(exist_ok=True)
            filepath = county_dir / f"{category}.json"
            if filepath.exists():
                print(f"Already exists, skipping")
                completed += 1
                continue

            # Execute query
            result = query_overpass(query_str)

            if result:
                # Save to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                elements_count = len(result.get('elements', []))
                print(f"✓ Saved {elements_count} elements to {filepath}")
            else:
                print("✗ Failed to retrieve data")

            completed += 1

    print("\nAll queries completed!")


if __name__ == "__main__":
    main()
