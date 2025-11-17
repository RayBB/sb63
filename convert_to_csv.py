#!/usr/bin/env -S uv run --script
"""
Convert OSM data from JSON files to CSV files.

For each element:
- Skip elements with only id, type, and lat/lon (geometry-only)
- For ways: get lat/lon from first node in the elements array
- Add query_purpose (filename) and query_county (folder name)
- Flatten all tags into columns

Output: Either one combined CSV file or separate CSV files by query type in data/csv/
Set CREATE_SEPARATE_CSV_FILES = True in main() to create separate files, False for combined file.

Run using `uv run --script convert_to_csv.py`
"""

import json
import pandas as pd
from pathlib import Path
from query_osm import COUNTIES, QUERIES


def create_node_lookup(elements):
    """
    Create a lookup dict for node coordinates from the elements array.
    Returns dict: node_id -> (lat, lon)
    """
    lookup = {}
    for element in elements:
        if element.get('type') == 'node' and 'lat' in element and 'lon' in element:
            lookup[element['id']] = (element['lat'], element['lon'])
    return lookup


def should_include_element(element, node_lookup):
    """
    Determine if element should be included.
    Skip elements that only have id, type, and basic geometry.
    """
    # Must have meaningful tags beyond just basic identification
    tags = element.get('tags', {})

    # Skip if no tags at all
    if not tags:
        return False

    # Check for at least one meaningful tag
    meaningful_keys = {'name', 'amenity', 'shop', 'building', 'leisure', 'religion',
                      'phone', 'website', 'addr:housenumber', 'addr:street',
                      'addr:city', 'email', 'opening_hours'}

    for key in tags.keys():
        if key in meaningful_keys or not key.startswith(('source', 'gnis', 'wikidata',
                                                         'wikipedia', 'note', 'fixme')):
            return True

    return False


def get_element_coordinates(element, node_lookup):
    """
    Extract latitude and longitude from element.
    For nodes: use their lat/lon directly.
    For ways: use coordinates of first node from lookup.
    """
    elem_type = element.get('type')

    if elem_type == 'node':
        return element.get('lat'), element.get('lon')
    elif elem_type == 'way':
        # For ways, get coordinates from first node
        nodes = element.get('nodes', [])
        if nodes:
            lat_lon = node_lookup.get(nodes[0])
            if lat_lon:
                return lat_lon[0], lat_lon[1]

    return None, None


def extract_element_data(element, node_lookup, query_purpose, query_county):
    """
    Extract all relevant data from a single element.
    Returns a dict with flattened data ready for DataFrame.
    """
    lat, lon = get_element_coordinates(element, node_lookup)

    data_row = {
        'latitude': lat,
        'longitude': lon,
        'query_purpose': query_purpose,
        'query_county': query_county,
        'osm_id': element.get('id'),
        'osm_type': element.get('type')
    }

    # Add all tags as individual columns
    tags = element.get('tags', {})
    for key, value in tags.items():
        data_row[key] = value

    return data_row


def process_json_file(filepath, query_purpose, query_county):
    """
    Process a single JSON file and return list of data rows.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        elements = data.get('elements', [])
        node_lookup = create_node_lookup(elements)

        rows = []
        for element in elements:
            if should_include_element(element, node_lookup):
                row_data = extract_element_data(element, node_lookup, query_purpose, query_county)
                rows.append(row_data)

        print(f"Processed {filepath} ({len(rows)} elements with meaningful data)")
        return rows

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return []


def main():
    """Main function to process all JSON files and create CSV files."""
    # Set to True to create separate CSV files by query type, False to create one combined CSV file
    CREATE_SEPARATE_CSV_FILES = True

    data_dir = Path("data")
    if not data_dir.exists():
        print("Error: data/ directory not found")
        return

    csv_dir = data_dir / "csv"
    csv_dir.mkdir(exist_ok=True)

    print("Starting data conversion to CSV...")

    # Collect all data
    all_data = []

    # Process each county directory
    for county_dir in sorted(data_dir.iterdir()):
        if not county_dir.is_dir():
            continue

        query_county = county_dir.name
        if query_county not in COUNTIES:
            print(f"Skipping unknown county directory: {query_county}")
            continue

        print(f"\nProcessing county: {query_county}")

        # Process each JSON file in county directory
        for json_file in sorted(county_dir.glob("*.json")):
            query_purpose = json_file.stem  # filename without .json extension
            if query_purpose not in QUERIES:
                print(f"Skipping unknown query file: {query_purpose}")
                continue

            rows = process_json_file(json_file, query_purpose, query_county)
            all_data.extend(rows)

    # Create CSV files
    if not all_data:
        print("No data to convert!")
        return

    df_all = pd.DataFrame(all_data)

    # Filter out rows where religion column is 'no' or 'none'
    religion_mask = ~df_all['religion'].isin(['no', 'none'])
    df_all = df_all[religion_mask]

    # Add blank columns to match more closely to expected columns 
    df_all['Collaborated'] = ''
    df_all['city'] = ''
    df_all['person_with_relationship'] = ''
    df_all['org_contact'] = ''
    df_all['org_contact_title'] = ''

    # Reorder columns to put specified columns first
    priority_cols = ['name', 'Collaborated', 'query_county', 'city', 'query_purpose', 'person_with_relationship', 'org_contact', 'org_contact_title', 'phone', 'email', 'contact:email', 'website']
    remaining_base_cols = ['latitude', 'longitude', 'osm_id', 'osm_type']
    other_cols = [col for col in df_all.columns if col not in priority_cols + remaining_base_cols]
    col_order = priority_cols + remaining_base_cols + sorted(other_cols, key=lambda x: (x.startswith('addr:'), x))

    # For dropping empty tag columns later
    tag_columns = other_cols

    total_rows = 0
    csv_files_created = 0

    if CREATE_SEPARATE_CSV_FILES:
        # Group by query_purpose and create separate CSV files
        purpose_groups = df_all.groupby('query_purpose')

        for purpose, group_df in purpose_groups:
            # Reorder columns and sort
            group_df = group_df[col_order]
            group_df = group_df.sort_values(['query_county', 'osm_id'])

            # Drop tag columns that are completely empty (all NaN or empty strings)
            columns_to_drop = []
            for col in tag_columns:
                if col in group_df.columns and (group_df[col].isna() | (group_df[col] == '')).all():
                    columns_to_drop.append(col)

            if columns_to_drop:
                group_df = group_df.drop(columns=columns_to_drop)
                print(f"Dropped {len(columns_to_drop)} empty tag columns from {purpose}")

            # Export to CSV
            csv_path = csv_dir / f"{purpose}.csv"
            group_df.to_csv(csv_path, index=False)
            print(f"Created {csv_path} ({len(group_df)} rows, {len(group_df.columns)} columns)")

            total_rows += len(group_df)
            csv_files_created += 1
    else:
        # Create single combined CSV file
        df_all = df_all[col_order]
        df_all = df_all.sort_values(['query_county', 'query_purpose', 'osm_id'])

        # Export to CSV (back to original location)
        csv_path = csv_dir / "combined_data.csv"
        df_all.to_csv(csv_path, index=False)
        print(f"Created {csv_path} ({len(df_all)} rows)")

        total_rows = len(df_all)
        csv_files_created = 1

    print("\nDone!")
    print(f"Total CSV files created: {csv_files_created}")
    print(f"Total rows across all files: {total_rows}")

    # Show summary stats
    purpose_counts = df_all.groupby('query_purpose').size()
    county_counts = df_all.groupby('query_county').size()

    print("\nData by purpose:")
    for purpose, count in purpose_counts.items():
        print(f"  {purpose}: {count} rows")

    print("\nData by county:")
    for county, count in county_counts.items():
        print(f"  {county}: {count} rows")


if __name__ == "__main__":
    main()
