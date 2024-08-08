import warnings
from typing import List, Union, Dict, Any, Tuple, Optional, Union

from notion_client import Client
from pydantic import BaseModel, TypeAdapter

from notion_df.base import (
    RichTextObject,
    SelectOption,
    DateObject,
    RelationObject,
    UserObject,
    RollupObject,
    FileObject,
    EmojiObject,
    FormulaObject,
    NotionExtendedColorEnum,
)


class ParentObject(BaseModel):
    type: str
    database_id: Optional[str] = None
    page_id: Optional[str] = None
    workspace: Optional[bool] = None
    block_id: Optional[str] = None


# BaseClasses
class BaseAttributes(BaseModel):
    pass


class BaseAttributeWithChildren(BaseModel):
    children: Optional[List["BaseNotionBlock"]] = None


class TextBlockAttributes(BaseAttributeWithChildren):
    rich_text: List[RichTextObject]
    color: Optional[NotionExtendedColorEnum] = None


class HeadingBlockAttributes(BaseAttributeWithChildren):
    rich_text: List[RichTextObject]
    color: Optional[NotionExtendedColorEnum] = None
    is_toggleable: bool
    # Whether or not the heading block is a toggle heading or not. If true, the heading block has toggle and can support children. If false, the heading block is a normal heading block.


class CalloutBlockAttributes(BaseAttributeWithChildren):
    rich_text: List[RichTextObject]
    icon: Optional[Union[FileObject, EmojiObject]] = None
    color: Optional[NotionExtendedColorEnum] = None


class ToDoBlockAttributes(BaseAttributeWithChildren):
    rich_text: List[RichTextObject]
    color: Optional[NotionExtendedColorEnum] = None
    checked: Optional[bool] = None


class CodeBlockAttributes(BaseAttributes):
    rich_text: List[RichTextObject]
    caption: Optional[List[RichTextObject]] = None
    language: Optional[str] = None  # TODO: it's actually an enum


class ChildPageAttributes(BaseAttributes):
    title: List[RichTextObject]


class EmbedBlockAttributes(BaseAttributes):
    url: str


class ImageBlockAttributes(BaseAttributes, FileObject):
    caption: Optional[List[RichTextObject]] = None
    # This is not listed in the docs, but it is in the API response (Nov 2022)


class VideoBlockAttributes(BaseAttributes):
    video: FileObject


class FileBlockAttributes(BaseAttributes):
    file: FileObject
    caption: Optional[List[RichTextObject]] = None


class PdfBlockAttributes(BaseAttributes):
    pdf: FileObject


class BookmarkBlockAttributes(BaseAttributes):
    url: str
    caption: Optional[List[RichTextObject]] = None


class EquationBlockAttributes(BaseAttributes):
    expression: str


class TableOfContentsAttributes(BaseAttributes):
    color: Optional[NotionExtendedColorEnum] = None


class LinkPreviewAttributes(BaseAttributes):
    url: str


class LinkToPageAttributes(BaseAttributes):
    type: str
    page_id: Optional[str] = None
    database_id: Optional[str] = None


ATTRIBUTES_MAPPING = {
    _cls.__name__: _cls
    for _cls in BaseAttributes.__subclasses__()
    + BaseAttributeWithChildren.__subclasses__()
}


class BaseNotionBlock(BaseModel):
    object: str = "block"
    parent: Optional[ParentObject] = None
    id: Optional[str] = None
    type: Optional[str] = None
    created_time: Optional[str] = None
    # created_by
    last_edited_time: Optional[str] = None
    # created_by
    has_children: Optional[bool] = None
    archived: Optional[bool] = None
    type: str

    @property
    def children(self):
        return self.__getattribute__(self.type).children

    def set_children(self, value: Any):
        self.__getattribute__(self.type).children = value


class ParagraphBlock(BaseNotionBlock):
    type: str = "paragraph"
    paragraph: TextBlockAttributes


class HeadingOneBlock(BaseNotionBlock):
    type: str = "heading_1"
    heading_1: HeadingBlockAttributes


class HeadingTwoBlock(BaseNotionBlock):
    type: str = "heading_2"
    heading_2: HeadingBlockAttributes


class HeadingThreeBlock(BaseNotionBlock):
    type: str = "heading_3"
    heading_3: HeadingBlockAttributes


class CalloutBlock(BaseNotionBlock):
    type: str = "callout"
    callout: CalloutBlockAttributes


class QuoteBlock(BaseNotionBlock):
    type: str = "quote"
    quote: TextBlockAttributes


class BulletedListItemBlock(BaseNotionBlock):
    type: str = "bulleted_list_item"
    bulleted_list_item: TextBlockAttributes


class NumberedListItemBlock(BaseNotionBlock):
    type: str = "numbered_list_item"
    numbered_list_item: TextBlockAttributes


class ToDoBlock(BaseNotionBlock):
    type: str = "to_do"
    to_do: ToDoBlockAttributes


class ToggleBlock(BaseNotionBlock):
    type: str = "toggle"
    toggle: TextBlockAttributes


class CodeBlock(BaseNotionBlock):
    type: str = "code"
    code: CodeBlockAttributes


class ChildPageBlock(BaseNotionBlock):
    type: str = "child_page"
    child_page: ChildPageAttributes


class ChildDatabaseBlock(BaseNotionBlock):
    type: str = "child_database"
    child_database: ChildPageAttributes


class EmbedBlock(BaseNotionBlock):
    type: str = "embed"
    embed: EmbedBlockAttributes


class ImageBlock(BaseNotionBlock):
    type: str = "image"
    image: ImageBlockAttributes


class VideoBlock(BaseNotionBlock):
    type: str = "video"
    video: VideoBlockAttributes


class FileBlock(BaseNotionBlock):
    type: str = "file"
    file: FileBlockAttributes


class PdfBlock(BaseNotionBlock):
    type: str = "pdf"
    pdf: PdfBlockAttributes


class BookmarkBlock(BaseNotionBlock):
    type: str = "bookmark"
    bookmark: BookmarkBlockAttributes


class EquationBlock(BaseNotionBlock):
    type: str = "equation"
    equation: EquationBlockAttributes


class DividerBlock(BaseNotionBlock):
    type: str = "divider"
    divider: Optional[Dict] = None


class TableOfContentsBlock(BaseNotionBlock):
    type: str = "table_of_contents"
    table_of_contents: TableOfContentsAttributes


class BreadcrumbBlock(BaseNotionBlock):
    type: str = "breadcrumb"
    breadcrumb: Optional[Dict] = None


# TODO: Column List and Column Blocks


class LinkPreviewBlock(BaseNotionBlock):
    type: str = "link_preview"
    link_preview: LinkPreviewAttributes


# TODO: Template blocks


class LinkToPageBlock(BaseNotionBlock):
    type: str = "link_to_page"
    link_to_page: LinkToPageAttributes


# TODO: Synced Block blocks

# TODO: Table blocks

# TODO: Table row blocks

BLOCKS_MAPPING = {
    list(_cls.model_fields.keys())[-1]: _cls for _cls in BaseNotionBlock.__subclasses__()
}


def parse_one_block(data: Dict) -> BaseNotionBlock:
    if data["type"] not in BLOCKS_MAPPING:
        warnings.warn(f"Unknown block type: {data['type']}")
        return None
    adapter = TypeAdapter(BLOCKS_MAPPING[data["type"]])
    return adapter.validate_python(data)


def parse_blocks(
    data: List[Dict], recursive: bool = False, client: Client = None
) -> List[BaseNotionBlock]:
    all_blocks = []
    for block_data in data:
        block = parse_one_block(block_data)
        if block.has_children and recursive and client:
            block.set_children(
                parse_blocks(
                    client.blocks.children.list(block_id=block.id)["results"],
                    recursive=recursive,
                    client=client,
                )
            )
        all_blocks.append(block)
    return all_blocks
