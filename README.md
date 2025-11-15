# sb63
Regional Transit Funding Measure for California Senate Bill 63

## Overview
This project includes tools for collecting geospatial data from OpenStreetMap (OSM) to support transit funding analysis across five Bay Area counties: Alameda, Contra Costa, San Francisco, San Mateo, and Santa Clara.

## OSM Data Querying Tool

### Purpose
The `query_osm.py` script queries OpenStreetMap data for five categories of amenities within each county:
- **Religion**: Places of worship, temples, churches, mosques, etc.
- **Community**: Social facilities, arts centers, community centers
- **Events**: Theatres, nightclubs, stadiums, event venues, marketplaces, etc.
- **Bikeshops**: Bicycle shops and related services
- **Bookstores**: Book shops and libraries

### Data Output
Raw JSON responses from the Overpass API are saved in the `data/` directory with this structure:
```
data/
├── county_name/
│   ├── bikeshops.json
│   ├── bookstores.json
│   ├── events.json
│   ├── religion.json
│   └── social_community.json
```

### Prerequisites
- Python 3.13+
- `uv` package manager

### Running the Script
```bash
# Install dependencies in virtual environment
uv sync

# Execute the queries (downloads ~7MB of JSON data)
uv run python query_osm.py
```

The script includes retry logic with exponential backoff to handle API rate limits and will skip already-downloaded data on subsequent runs.

### Data Processing
The collected JSON files contain raw OpenStreetMap elements (nodes, ways, relations) with metadata. Process these files as needed for transit planning analysis.
