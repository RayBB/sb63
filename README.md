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

## CSV Conversion Tool

### Purpose
The `uv run convert_to_csv.py` script processes all JSON data files into a single consolidated CSV file for analysis. It:

- **Filters out geometry-only elements**: Skips OSM elements that only contain basic location data without meaningful attributes
- **Handles both nodes and ways**: For ways (polygonal features), uses coordinates from the first node; for nodes, uses their direct coordinates
- **Adds metadata columns**: Includes `query_purpose` (derived from filename) and `query_county` (derived from folder name)
- **Flattens OSM tags**: Converts all OpenStreetMap key-value tag pairs into individual CSV columns
- **Organizes columns**: Places location data, metadata, and OSM identifiers first, followed by all tag columns

### Data Processing Details

The script processes each JSON file individually:
- Creates a coordinate lookup for all nodes in the file
- Filters elements to include only those with meaningful tags (names, amenities, shops, buildings, etc.)
- For each included element, extracts latitude/longitude and flattens all tags into columns
- Combines data from all 5 counties × 5 categories = 25 input files

### Output Format
Generates a single `osm_data.csv` file with:
- **5,168 rows** of processed geospatial data
- **463 columns** dynamically discovered from OSM tags
- Location columns: `latitude`, `longitude`, `query_purpose`, `query_county`, `osm_id`, `osm_type`
- Tag columns: All OSM tags (name, amenity, addr:*, shop, website, phone, etc.)

### Usage
```bash
# Run after collecting JSON data
uv run python convert_to_csv.py
```

The script includes progress logging for each file processed and summary statistics by county and category.

### Data Processing
The collected JSON files contain raw OpenStreetMap elements (nodes, ways, relations) with metadata. The CSV conversion provides a clean, flat format suitable for spreadsheet analysis, database import, or data science workflows.
