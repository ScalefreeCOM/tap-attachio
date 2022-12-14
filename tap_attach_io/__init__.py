#!/usr/bin/env python3
import os
import json
from sqlite3 import threadsafety
import singer
from singer import utils, metadata, metrics
from singer.catalog import Catalog, CatalogEntry
from singer.schema import Schema
import requests
from tap_attach_io.context import Context
from datetime import date

BASE_URL = "https://api.attach.io/v1/"
REQUIRED_CONFIG_KEYS = ["api_key"]
LOGGER = singer.get_logger()


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schemas():
    """ Load schemas from schemas folder """
    schemas = {}
    for filename in os.listdir(get_abs_path('schemas')):
        path = get_abs_path('schemas') + '/' + filename
        file_raw = filename.replace('.json', '')
        with open(path) as file:
            schemas[file_raw] = Schema.from_dict(json.load(file))
    return schemas

# relevant for generating catalogue.json with --discover argument
def discover():
    raw_schemas = load_schemas()
    streams = []
    for stream_id, schema in raw_schemas.items():
        stream_metadata = []
        key_properties = []
        streams.append(
            CatalogEntry(
                tap_stream_id=stream_id,
                stream=stream_id,
                schema=schema,
                key_properties=key_properties,
                metadata=stream_metadata,
                replication_key=None,
                is_view=None,
                database=None,
                table=None,
                row_count=None,
                stream_alias=None,
                replication_method=None,
            )
        )
    return Catalog(streams)

#Generating urls for request-objects
def sync_stream(streamname):

    if streamname == 'links_visits':
        for id in get_list_of_ids(name='links'):        
            url = f"{BASE_URL}links/{id}/visits?api_key={Context.config.get('api_key')}"
            response = requests.get(url)
            LOGGER.info("API request: " + url)
            first_page = response.text
            response_json = json.loads(first_page)
            yield response_json
            
    elif streamname == 'documents_visits':
        for id in get_list_of_ids(name='documents'):        
            url = f"{BASE_URL}documents/{id}/visits?api_key={Context.config.get('api_key')}"
            response = requests.get(url)
            LOGGER.info("API request: " + url)
            first_page = response.text
            response_json = json.loads(first_page)
            yield response_json   
            
    else:
        url = f"{BASE_URL}{streamname}/?api_key={Context.config.get('api_key')}"
        response = requests.get(url)
        LOGGER.info("API request: " + url)
        first_page = response.text
        response_json = json.loads(first_page)
        yield response_json

# relevant for schemas documents_visits and link_visits because visits can olny be queried (link/document)-id-dependent
def get_list_of_ids(name):
    url = f"{BASE_URL}{name}/?api_key={Context.config.get('api_key')}"
    response = requests.get(url)
    first_page = response.text
    response_json = json.loads(first_page)
    ids = []
    for elem in response_json:
       ids.append(elem['id'])
    return ids

    
#writing the records  
def sync(config, state, catalog):
    """ Sync data from tap source """
    # Loop over selected streams in catalog
    counter = 0
    for stream in catalog.get_selected_streams(state):
        LOGGER.info("Syncing stream:" + stream.tap_stream_id)

        bookmark_column = stream.replication_key
        is_sorted = True  # TODO: indicate whether data is sorted ascending on bookmark value

        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties,
        )

        
        with singer.metrics.record_counter(endpoint=stream.tap_stream_id) as counter:
            try:
                for request in sync_stream(stream.tap_stream_id):
                    for row in request:
                        singer.write_record(stream.tap_stream_id, row)
                        if bookmark_column:
                            if is_sorted:
                                # update bookmark to latest value
                                singer.write_state({stream.tap_stream_id: row[bookmark_column]})
                            else:
                                # if data unsorted, save max value until end of writes
                                max_bookmark = max(max_bookmark, row[bookmark_column])
                        counter.increment() 
            except Exception as e:
                pass


def main():
    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    LOGGER.debug(f"Argumentss: {args}")

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover()
        catalog.dump()
    # Otherwise run in sync mode
    else:
        Context.tap_start = utils.now()
        LOGGER.info("Tap Start: " + str(Context.tap_start))
        if args.catalog:
            Context.catalog = args.catalog#.to_dict()
            #LOGGER.info(f"Catalog: {catalog}")
        else:
            Context.catalog = discover()
            
        Context.config = args.config
        Context.state = args.state

        sync(Context.config, Context.state, Context.catalog)


if __name__ == "__main__":
    main()
    
