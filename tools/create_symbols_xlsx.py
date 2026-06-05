from __future__ import annotations

import html
import zipfile
from pathlib import Path


SHEETS = {
    "US": [
        ["symbol", "name", "enabled", "industry"],
        ["AAPL", "Apple", "TRUE", "Consumer Electronics"],
        ["MSFT", "Microsoft", "TRUE", "Software"],
        ["NVDA", "NVIDIA", "TRUE", "Semiconductors"],
        ["SPY", "S&P 500 ETF", "TRUE", "ETF"],
        ["QQQ", "Nasdaq 100 ETF", "TRUE", "ETF"],
    ],
    "HK": [
        ["symbol", "name", "enabled", "industry"],
        ["0700.HK", "Tencent", "TRUE", "Internet"],
        ["9988.HK", "Alibaba HK", "TRUE", "E-commerce"],
        ["3690.HK", "Meituan", "TRUE", "Consumer Services"],
    ],
}


def main() -> None:
    write_xlsx(Path("symbols.xlsx"), SHEETS)


def write_xlsx(path: Path, sheets: dict[str, list[list[str]]]) -> None:
    shared_strings: list[str] = []
    shared_index: dict[str, int] = {}

    def shared(value: str) -> int:
        if value not in shared_index:
            shared_index[value] = len(shared_strings)
            shared_strings.append(value)
        return shared_index[value]

    sheet_xml: dict[str, str] = {}
    for sheet_name, rows in sheets.items():
        sheet_rows = []
        for row_idx, row in enumerate(rows, start=1):
            cells = []
            for col_idx, value in enumerate(row):
                ref = f"{column_name(col_idx)}{row_idx}"
                cells.append(f'<c r="{ref}" t="s"><v>{shared(value)}</v></c>')
            sheet_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
        sheet_xml[sheet_name] = f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{"".join(sheet_rows)}</sheetData>
</worksheet>"""

    shared_items = "".join(
        f"<si><t>{html.escape(value)}</t></si>" for value in shared_strings
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types(len(sheets)))
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/workbook.xml", workbook_xml(list(sheets)))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels(len(sheets)))
        for idx, (_, xml) in enumerate(sheet_xml.items(), start=1):
            archive.writestr(f"xl/worksheets/sheet{idx}.xml", xml)
        archive.writestr(
            "xl/sharedStrings.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{shared_items}</sst>""",
        )


def content_types(sheet_count: int) -> str:
    sheet_overrides = "\n".join(
        f'  <Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = "\n".join(
        f'    <sheet name="{html.escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, name in enumerate(sheet_names, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
{sheets}
  </sheets>
</workbook>"""


def workbook_rels(sheet_count: int) -> str:
    sheet_rels = "\n".join(
        f'  <Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    shared_id = sheet_count + 1
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{sheet_rels}
  <Relationship Id="rId{shared_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>"""


def column_name(index: int) -> str:
    output = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        output = chr(ord("A") + remainder) + output
    return output


if __name__ == "__main__":
    main()
