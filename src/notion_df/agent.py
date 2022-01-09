from typing import List, Dict, Optional
from datetime import datetime
import warnings
import os
from functools import wraps

from notion_client import Client
from notion_client.helpers import get_id

from notion_df.values import PageProperties, PageProperty
from notion_df.configs import DatabaseSchema

API_KEY = None
NOT_REVERSE_DATAFRAME = -1
# whether to reverse the dataframe when performing uploading.
# for some reason, notion will reverse the order of dataframe
# when uploading.
# -1 for reversing, for not reversing


def config(api_key: str):
    global API_KEY
    API_KEY = api_key


def _load_api_key(api_key: str) -> str:
    if api_key is not None:
        return api_key
    elif API_KEY is not None:
        return API_KEY
    elif os.environ.get("NOTION_API_KEY") is not None:
        return os.environ.get("NOTION_API_KEY")
    else:
        raise ValueError("No API key provided")


def _is_notion_database(notion_url):
    return "?v=" in notion_url.split("/")[-1]


def use_client(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        orig_client = client = kwargs.pop("client", None)

        if client is None:
            api_key = _load_api_key(kwargs.pop("api_key", None))
            client = Client(auth=api_key)
        out = func(client=client, *args, **kwargs)

        if orig_client is None:
            # Automatically close the client if it was not passed in
            client.close()
        return out

    return wrapper


@use_client
def load(notion_url: str, *, api_key: str = None, client: Client = None):
    assert _is_notion_database(notion_url)
    database_id = get_id(notion_url)

    query_results = client.databases.query(database_id=database_id)
    assert query_results["object"] == "list"
    properties = PageProperties.from_raw(
        query_results["results"]
    )  # TODO: handle pagination

    retrieve_results = client.databases.retrieve(database_id=database_id)
    schema = DatabaseSchema.from_raw(retrieve_results["properties"])

    df = properties.to_frame()
    df.schema = schema
    return df


def create_database(
    page_id: str, client: Client, schema: DatabaseSchema, title: str = ""
):
    response = client.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"type": "text", "text": {"content": title}}],
        properties=schema.query_dict(),
    )
    assert response["object"] == "database"
    return response


def upload_row_to_database(row, database_id, schema, client):

    properties = PageProperty.from_series(row, schema).query_dict()
    client.pages.create(parent={"database_id": database_id}, properties=properties)


def upload_to_database(df, databse_id, schema, client, errors):
    for _, row in df[::NOT_REVERSE_DATAFRAME].iterrows():
        try:
            upload_row_to_database(row, databse_id, schema, client)
        except Exception as e:
            if errors == "strict":
                raise e
            elif errors == "warn":
                warnings.warn(f"Encountered errors {e} while uploading row: {row}")
            elif errors == "ignore":
                continue


def load_database_schema(database_id, client):
    return DatabaseSchema.from_raw(
        client.databases.retrieve(database_id=database_id)["properties"]
    )


@use_client
def upload(
    df: "pd.DataFrame",
    notion_url: str,
    schema: DatabaseSchema = None,
    mode: str = "a",
    title: str = "",
    title_col: str = "",
    errors: str = "strict",
    *,
    api_key: str = None,
    client: Client = None,
):
    """Upload a dataframe to the specified Notion database.

    Args:
        df (pd.DataFrame):
            The dataframe to upload.
        notion_url (str):
            The URL of the Notion page to upload to.
            If it is a notion page, then it will create a new database
            under that page and upload the dataframe to it.
        schema (DatabaseSchema, optional):
            The schema of the Notion database.
            When not set, it will be inferred from (1) the target
            notion database (if it is) then (2) the dataframe itself.
        mode (str, optional):
            (the function is not supported yet.)
            Whether to append to the database or overwrite.
            Defaults to "a".
        title (str, optional):
            The title of the Notion database.
            Defaults to "".
        title_col (str, optional):
            Every Notion database requires a "title" column.
            When the schema is not set, by default it infers the first
            column of uploaded dataframe as the title column. You can
            set this value to specify the title column.
            Defaults to "".
        errors (str, optional):
            Since we upload the dataframe to Notion row by row, you
            can specify how to handle errors during uploading. There
            are several options:
                1. "strict": raise an error when there is one.
                2. "ignore": ignore errors and continue uploading
                    subsequent rows.
                3. "warn": print the error message and continue uploading
            Defaults to "strict".
        api_key (str, optional):
            The API key of the Notion integration.
            Defaults to None.
        client (Client, optional):
            The notion client.
            Defaults to None.
    """
    if schema is None:
        if hasattr(df, "schema"):
            schema = df.schema

    if not _is_notion_database(notion_url):
        if schema is None:
            schema = DatabaseSchema.from_df(df, title_col=title_col)
        database_properties = create_database(get_id(notion_url), client, schema, title)
        databse_id = database_properties["id"]
        notion_url = database_properties["url"]
    else:
        databse_id = get_id(notion_url)
        if schema is None:
            schema = load_database_schema(databse_id, client)

    # At this stage, we should have the appropriate schema
    assert schema is not None

    if not schema.is_df_compatible(df):
        raise ValueError(
            "The dataframe is not compatible with the database schema."
            "The df contains columns that are not in the databse: "
            + f"{[col for col in df.columns if col not in schema.configs.keys()]}"
        )

    if mode not in ("a", "append"):
        raise NotImplementedError
        # TODO: clean the current values in the notion database (if any)

    df = schema.transform(df)
    upload_to_database(df, databse_id, schema, client, errors)

    print(f"Your dataframe has been uploaded to the Notion page: {notion_url} .")
    return notion_url
