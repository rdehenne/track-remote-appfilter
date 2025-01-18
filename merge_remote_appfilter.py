#!/usr/bin/env python3

"""
Use a remote appfilter.xml file to add missing items to the local appfilter.xml.


Usage: `./merge_remote_appfilter.py <path/to/local-appfilter.xml> <https://url.to/remote-appfilter.xml>`
Sample invocation:
`./merge_remote_appfilter.py newicons/appfilter.xml https://raw.githubusercontent.com/Arcticons-Team/Arcticons/refs/heads/main/newicons/appfilter.xml`

This script uses the fact that the same drawable can be used by multiple components.
When multiple components from the remote appfilter.xml use the same drawable,
and the local appfilter.xml contains at least one of these components,
we can safely add all components with that share the same drawable in the remote
appfilter to the local appfilter.

If drawable names are different between remote and local for a given component,
the items added to the local appfilter correctly use the drawable name
from the local appfilter.

Currently does not handle `<calendar>` elements.

Example:
The remote appfilter.xml contains these entries:
    ```
    (component="comp1", drawable="remote1")
    (component="comp2", drawable="remote1")
    (component="comp3", drawable="remote2")
    ```
and the local appfilter.xml contains this entry:
    ```
    (component="comp1", drawable="local1")
    ```
then the resulting local appfilter.xml will now contain:
    ```
    (component="comp1", drawable="local1")
    (component="comp2", drawable="local1") # <- inferred by script
    ```
"""

import logging
import re
import requests
import sys

from os import PathLike
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Matches appfilter items such as:
# `<item component="ComponentInfo{acr.browser.lightning/acr.browser.lightning.MainActivity}" drawable="lightning"/>`
ITEM_REGEX = re.compile(r'component="([^"]+)".*drawable="([^"]+)"')

# Matches appfilter items, but ignore default Android components, e.g. `component=":BROWSER"`
# We do not want new items to be added to the `<!-- default -->` section
ITEM_REGEX_IGNORE_DEFAULT = re.compile(
    r'component="(ComponentInfo[^"]+)".*drawable="([^"]+)"')

# Indentation format of the output appfilter file
APPFILTER_INDENT = "\t"


def to_local_component_drawables(path: PathLike | str) -> dict[str, str]:
    """
    Parse appfilter items from `path` into a
    `{component: drawable}` dictionary.
    """
    components_to_drawables = {}

    with open(path) as file:
        lines = file.readlines()

        for line in lines:
            match = ITEM_REGEX.search(line)

            if match is not None:
                component = match.group(1)
                drawable = match.group(2)

                components_to_drawables[component] = drawable

    return components_to_drawables


@dataclass
class AppFilterItem:
    component: str
    drawable: str

    def __str__(self):
        return f'<item component="{self.component}" drawable="{self.drawable}"/>'


@dataclass
class RemoteComparison:
    """
    Stores the result of a comparison between remote and local appfilter files.

    Attributes:
        remote_to_local_drawable: An equivalence table of drawable names between remote and local
        missing_items_local: The list of appfilter items that are present in remote but not in local.
                             The items' drawable names are those of the remote appfilter.
    """
    remote_to_local_drawable: dict[str, str]
    missing_items_local: list[AppFilterItem]


def remote_match_drawables(local_component_dict: dict[str, str], remote_content: str) -> RemoteComparison:
    """
    Compare items between local and remote, and return a RemoteComparison object.

    - If a component is in both local and remote files, add a `remote_drawable -> local_drawable`
    entry into the equivalency dictionary `remote_to_local_drawable`.
    - If an item is in remote but not in local, add it to `missing_items_local`.
    """
    remote_to_local_drawable: dict[str, str] = {}
    missing_items_local = []

    matches = ITEM_REGEX.finditer(remote_content)

    for match in matches:
        component = match.group(1)
        remote_drawable = match.group(2)

        if component in local_component_dict:
            # Component exists in both local and remote appfilter,
            # add entry remote_drawable -> local_drawable
            local_drawable = local_component_dict[component]
            existing_local_drawable = remote_to_local_drawable.get(component)

            if existing_local_drawable and local_drawable != existing_local_drawable:
                # There is already a local drawable for this remote drawable,
                # do not override existing local drawable with another drawable.
                # This happens when the remote appfilter uses the same drawable
                # for multiple components, but the local appfilter has different
                # drawables for those components.

                logger.warning(
                    f'Multiple local drawables found for remote drawable "{remote_drawable}"')
                logger.debug(
                    f'Keeping existing local drawable "{existing_local_drawable}", ignoring new drawable "{local_drawable}"')
            else:
                # No existing local drawable for remote drawable,
                # saving remote_drawable -> local_drawable match
                remote_to_local_drawable[remote_drawable] = local_drawable
        else:
            # Component only exists in remote appfilter, save item for later
            logger.debug(
                f'Component "{component}" does not exist in local appfilter')
            missing_items_local.append(
                AppFilterItem(component, remote_drawable))

    return RemoteComparison(remote_to_local_drawable, missing_items_local)


def generate_missing_items(remote_comparison: RemoteComparison) -> dict[str, list[str]]:
    """
    Return appfilter items that are missing from local, but whose
    drawable can be determined from the equivalency dictionary.

    The return dictionary contains, for each drawable from local,
    the list of components that could be inferred from remote.
    (The dictionary contains only drawables for which at least
    one component could be inferred)
    """

    local_drawable_to_components: dict[str, list[str]] = {}

    for missing_item in remote_comparison.missing_items_local:
        local_drawable_equivalent = remote_comparison.remote_to_local_drawable.get(
            missing_item.drawable)

        if local_drawable_equivalent:
            # Create or append component to the list of components with the same drawable
            if local_drawable_to_components.get(local_drawable_equivalent):
                local_drawable_to_components[local_drawable_equivalent].append(
                    missing_item.component)
            else:
                local_drawable_to_components[local_drawable_equivalent] = [
                    missing_item.component]

        else:
            logger.debug(
                f'No equivalent for drawable "{missing_item.drawable}" in local appfilter')

    return local_drawable_to_components


def write_insert_appfilter(input_local_path: PathLike | str, output_path: PathLike | str, drawable_to_components: dict[str, list[str]]):
    """
    Insert new components into the appfilter file, right after the last `<item>`
    that uses the same drawable.

    Write into `output_path` the same content than `input_local_path`, plus
    the extra items generated from this script.
    """
    new_lines = []

    with open(input_local_path) as file:
        lines = file.readlines()

        # Scan in reverse order to insert the new item after all
        # items that use the same drawable
        for line in reversed(lines):
            match_if_item = ITEM_REGEX_IGNORE_DEFAULT.search(line)

            if match_if_item is not None:
                drawable = match_if_item.group(2)

                if drawable in drawable_to_components:
                    # There is at least one component we can insert
                    # after this item
                    for component in drawable_to_components[drawable]:
                        # Add the new items as XML elements
                        item = AppFilterItem(component, drawable)
                        new_lines.append(f"{APPFILTER_INDENT}{str(item)}\n")

                    # Prevent from writing the same items again
                    # if the drawable is used in other lines
                    del drawable_to_components[drawable]

            new_lines.append(line)

    with open(output_path, "w") as output_file:
        output_file.writelines(reversed(new_lines))


def main(local_appfilter_path: str, remote_appfilter_url: str) -> None:
    logging.basicConfig(level=logging.WARNING)
    logger.info("Started")

    local_component_dict = to_local_component_drawables(local_appfilter_path)

    try:
        remote_appfilter_text = requests.get(remote_appfilter_url).text
    except Exception as e:
        logger.error(f"Error downloading remote appfilter: {e}")
        sys.exit(1)

    remote_comparison = remote_match_drawables(
        local_component_dict, remote_appfilter_text)

    logger.debug(
        f"Missing items: {{k: v for k, v in remote_comparison.remote_to_local_drawables.items() if k != v}}")

    generated_items = generate_missing_items(remote_comparison)
    # TODO: write into local
    write_insert_appfilter(local_appfilter_path,
                           local_appfilter_path, generated_items)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        logger.error(
            f"Usage: {sys.argv[0]} <path/to/local-appfilter.xml> <https://url.to/remote-appfilter.xml>")
        sys.exit(2)

    in_out_local_path = sys.argv[1]
    remote_url = sys.argv[2]

    main(in_out_local_path, remote_url)
