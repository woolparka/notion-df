from typing import List, Optional, Any
from enum import Enum
from pydantic import field_validator, BaseModel
import pandas as pd

from notion_df.utils import is_time_string, is_uuid
from notion_df.constants import RICH_TEXT_CONTENT_MAX_LENGTH

### All colors supported in NOTION


class NotionColorEnum(str, Enum):
    Default = "default"
    Gray = "gray"
    Brown = "brown"
    Orange = "orange"
    Yellow = "yellow"
    Green = "green"
    Blue = "blue"
    Purple = "purple"
    Pink = "pink"
    Red = "red"


class NotionExtendedColorEnum(str, Enum):
    Default = "default"
    Gray = "gray"
    Brown = "brown"
    Orange = "orange"
    Yellow = "yellow"
    Green = "green"
    Blue = "blue"
    Purple = "purple"
    Pink = "pink"
    Red = "red"
    GrayBackground = "gray_background"
    BrownBackground = "brown_background"
    OrangeBackground = "orange_background"
    YellowBackground = "yellow_background"
    GreenBackground = "green_background"
    BlueBackground = "blue_background"
    PurpleBackground = "purple_background"
    PinkBackground = "pink_background"
    RedBackground = "red_background"


class RichTextTypeEnum(str, Enum):
    Text = "text"
    Mention = "mention"
    Equation = "equation"


class SelectOption(BaseModel):
    id: Optional[str] = None
    name: str
    color: Optional[NotionColorEnum] = None

    @classmethod
    def from_value(cls, value: str):
        return cls(name=value)

    @field_validator("name")
    @classmethod
    def name_cannot_contain_comma(cls, v):
        if "," in v:
            raise ValueError(f"Invalid option name {v} that contains comma")
        return v


class SelectOptions(BaseModel):
    options: Optional[List[SelectOption]] = None

    @classmethod
    def from_value(cls, values: List[str]):
        return cls(options=[SelectOption.from_value(value) for value in values])


class RelationObject(BaseModel):
    id: str
    # TODO: Change this to UUID validation

    @classmethod
    def from_value(cls, value: str):
        return cls(id=value)

    @field_validator("id")
    @classmethod
    def id_must_be_uuid(cls, v):
        if not is_uuid(v):
            raise ValueError(f"Invalid id {v}")
        return v


class UserObject(BaseModel):
    object: str = "user"
    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_value(cls, value: str):
        return cls(id=value)

    @field_validator("object")
    @classmethod
    def object_is_name(cls, v):
        if v != "user":
            raise ValueError(f"Invalid user object value {v}")
        return v

    @property
    def value(self):
        return self.name


class NumberFormat(BaseModel):
    format: str


class FormulaProperty(BaseModel):
    expression: str


class RelationProperty(BaseModel):
    database_id: str
    # TODO: Change this to UUID validation
    synced_property_name: Optional[str] = None
    synced_property_id: Optional[str] = None


class DateObject(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    time_zone: Optional[str] = None

    @field_validator("start")
    @classmethod
    def is_start_ISO8601(cls, v):
        # TODO: Currently it cannot suport time ranges
        if v is not None:
            if not is_time_string(v):
                raise ValueError(
                    "The data start is not appropriately formatted as an ISO 8601 date string."
                )
        return v

    @field_validator("end")
    @classmethod
    def is_end_ISO8601(cls, v):
        if v is not None:
            if not is_time_string(v):
                raise ValueError(
                    "The data end is not appropriately formatted as an ISO 8601 date string."
                )
        return v

    @classmethod
    def from_value(cls, value: str):
        return cls(start=value)
        # TODO: Now we assume the value has already been formated as strings
        # But we should parse them into appropriate formats.

    @property
    def value(self):
        return pd.to_datetime(self.start)
        # TODO: what should the data structure be if self.end is not None?


class RollupProperty(BaseModel):
    relation_property_name: Optional[str] = None
    relation_property_id: Optional[str] = None
    rollup_property_name: Optional[str] = None
    rollup_property_id: Optional[str] = None
    function: str
    # TODO: Change this to ENUM - https://developers.notion.com/reference/create-a-database#rollup-configuration


class RollupObject(BaseModel):
    type: str
    # TODO: Change this to ENUM - https://developers.notion.com/reference/property-value-object#rollup-property-values
    number: Optional[float] = None
    date: Optional[DateObject] = None
    array: Optional[List[Any]] = None
    # Based on the description in https://developers.notion.com/reference/property-value-object#rollup-property-value-element
    # Each element is exactly like property value object, but without the "id" key.
    # As there's a preprocess step in RollupValues, each item of the array must
    # be a property value object.
    function: Optional[str] = None
    # Though the function param doesn't appear in the documentation, it exists
    # in the return values of the API. Set it as optional for future compatibility.
    # TODO: check in the future if the function param should be updated.

    @field_validator("type")
    @classmethod
    def ensure_non_empty_data(cls, v):
        data_type = v
        if data_type is None:
            raise ValueError("RollupObject must have a type.")
        if data_type not in ["number", "date", "array"]:
            raise ValueError(f"RollupObject type {data_type} is invalid.")
        return v

    @property
    def value(self):
        if self.type == "number":
            return self.number
        if self.type == "date":
            if self.date is not None:
                return self.date.value
        if self.type == "array":
            return [ele.value for ele in self.array]


class FileTargetObject(BaseModel):
    url: str
    expiry_time: Optional[str] = None

    @property
    def value(self):
        return self.url


class FileObject(BaseModel):
    name: Optional[str] = None #TODO: Figure out why this is not required...
    type: str
    file: Optional[FileTargetObject] = None
    external: Optional[FileTargetObject] = None

    @property
    def value(self):
        if self.type == "file":
            if self.file is not None:
                return self.file.value
        else:
            if self.external is not None:
                return self.external.value


class FormulaObject(BaseModel):
    type: str
    string: Optional[str] = None
    number: Optional[float] = None
    boolean: Optional[bool] = None
    date: Optional[DateObject] = None

    @property
    def value(self):
        if self.type == "string":
            return self.string
        elif self.type == "number":
            return self.number
        elif self.type == "boolean":
            return self.boolean
        elif self.type == "date":
            if self.date is not None:
                return self.date.value


class AnnotationObject(BaseModel):
    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: NotionExtendedColorEnum


class TextLinkObject(BaseModel):
    type: Optional[str] = "url"
    url: str


class TextObject(BaseModel):
    content: str
    link: Optional[TextLinkObject] = None


class PageReferenceObject(BaseModel):
    id: str


class LinkPreviewMentionObject(BaseModel):
    url: str


class MentionObject(BaseModel):
    type: str
    user: Optional[UserObject] = None
    page: Optional[PageReferenceObject] = None
    database: Optional[PageReferenceObject] = None
    date: Optional[DateObject] = None
    link_preview: Optional[LinkPreviewMentionObject] = None


class EquationObject(BaseModel):
    expression: str


class BaseRichTextObject(BaseModel):
    plain_text: Optional[str] = None
    # TODO: The Optional[plain_text] is used when creating property values
    href: Optional[str] = None
    annotations: Optional[AnnotationObject] = None
    type: Optional[RichTextTypeEnum] = None

    @property
    def value(self):
        return self.plain_text


class RichTextObject(BaseRichTextObject):
    text: Optional[TextObject] = None
    mention: Optional[MentionObject] = None
    equation: Optional[EquationObject] = None

    @classmethod
    def from_value(cls, value: str):
        return cls(text=TextObject(content=value))

    @classmethod
    def encode_string(cls, value: str) -> List["RichTextObject"]:
        chunk_size = RICH_TEXT_CONTENT_MAX_LENGTH
        return [
            cls(text=TextObject(content=value[idx : idx + chunk_size]))
            for idx in range(0, len(value), chunk_size)
        ]


class EmojiObject(BaseModel):
    type: str = "emoji"
    emoji: str
