from urllib.parse import quote

CITY_MAP_VIEWPORTS = {
    "abu dhabi": "54.756359%2C24.560894%2F9.96",
    "al ain": "55.760559%2C24.207500%2F11.0",
    "sharjah": "55.405556%2C25.357500%2F11.5",
    "ajman": "55.479444%2C25.411111%2F12.0",
}


def build_search_query(city_name: str, query: str, country_tld: str = "ae") -> str:
    tld = country_tld.strip().lstrip(".")
    raw_city = city_name.strip().lower()
    encoded_query = quote(query.strip())

    if tld == "ae" and raw_city in CITY_MAP_VIEWPORTS:
        coords = CITY_MAP_VIEWPORTS[raw_city]
        return f"https://2gis.{tld}/dubai/search/{encoded_query}?m={coords}"

    return f"https://2gis.{tld}/{raw_city}/search/{encoded_query}"
