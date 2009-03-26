#!/usr/bin/env python
# 
# Copyright 2009 Maik Gosenshuis
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Converts .tmx files generated by the generic WYSIWYG map editor Tiled
(http://www.mapeditor.org) into a corresponding MapLayer to be used in cocos2d.

Currently, this deserializer only supports rectangle maps (orthogonal in Tiled).
You can deserialize a map by calling the load_map() method in this module.

Known bugs:

    - A small spacing occurs between tiles when the tile size is small. I am still
      unsure if this is caused by cocos or this module.
    - Does not support compression or base64 encoding yet, so make sure you disable
      those settings in Tiled.

Future features:

    - Support additional map formats (hexagonal, isometric).
    - Support for base64 encoding.
    - Support for gzip compression.
"""


import pyglet.image
import cocos.tiles
import xml.dom.minidom
import os.path


__all__ = ['load_map', 'MapException']


class MapException(Exception):
    """Indicates a problem with the map's data, not with its mark-up."""
    pass


def load_map(filename):
    """Creates a cocos2d RectMapLayer object based on the Tiled .tmx file."""
    doc = xml.dom.minidom.parse(filename)

    map_node = doc.documentElement
    
    # Only support orthogonal (rectangle) oriented maps for now.
    if map_node.getAttribute('orientation') <> 'orthogonal':
        raise MapException('tiled2cocos only supports orthogonal maps for now.')

    tile_width = int(map_node.getAttribute('tilewidth'))
    tile_height = int(map_node.getAttribute('tileheight'))

    # We want to find the absolute path to the directory containing our XML file
    # so we can create paths relative to the XML file, not from the current
    # working directory.
    root_dir = os.path.dirname(os.path.abspath(filename))
    
    tiles = load_tilesets(map_node, root_dir)
    
    gid_matrix = create_gid_matrix(map_node)

    cells = []
    for i, column in enumerate(gid_matrix):
        col = []
        
        for j, gid in enumerate(column):
            col.append(cocos.tiles.RectCell(i, j, tile_width, tile_height, {}, tiles[gid]))
            
        cells.append(col)

    rect_map = cocos.tiles.RectMapLayer('map', tile_width, tile_height, cells)

    # Properties on maps are not supported by default, but we can set properties as
    # an attribute ourselves.
    rect_map.properties = load_properties(map_node)

    return rect_map


def load_tilesets(map_node, root_dir):
    """Creates the cocos2d TileSet objects from .tmx tileset nodes."""
    tileset_nodes = map_node.getElementsByTagName('tileset')
    tiles = {}
    for tileset_node in tileset_nodes:
        if tileset_node.hasAttribute('source'):
            tileset_filename = tileset_node.getAttribute('source')
            tileset_doc = xml.dom.minidom.parse(os.path.join(root_dir, tileset_filename))
            real_node = tileset_doc.documentElement
            
            # The firstgid attribute in the external tileset file is meaningless,
            # since there is no way for it to be relative to the other tilesets in
            # in the map file.
            real_node.setAttribute('firstgid', tileset_node.getAttribute('firstgid'))
        else:
            real_node = tileset_node

        tiles.update(load_tiles(real_node, root_dir))
    
    return tiles


def load_tiles(tileset_node, root_dir):
    """Loads the tiles from one tileset."""
    tiles = {}

    tile_width = int(tileset_node.getAttribute('tilewidth'))
    tile_height = int(tileset_node.getAttribute('tileheight'))
    spacing = int(try_attribute(tileset_node, 'spacing', 0))
    
    # Margin support appears to be broken in Tiled (0.7.2), so it is disabled
    # for now.
    margin = 0

    image_atlas_file = get_first(tileset_node, 'image').getAttribute('source')
    image_atlas = pyglet.image.load(os.path.join(root_dir, image_atlas_file))

    # Load all tile properties for this tileset in one batch, instead of querying
    # them separately.
    tile_properties = load_tile_properties(tileset_node)

    gid = int(tileset_node.getAttribute('firstgid'))
    
    # Start at the top left corner of the image.
    y = image_atlas.height - tile_height
    while y >= 0:
        x = 0
        while x + tile_width <= image_atlas.width:
            # Extract the relevant portion from the atlas image.
            tile_image = image_atlas.get_region(x, y, tile_width, tile_height)            
            properties = tile_properties.get(gid, {})
            tiles[gid] = cocos.tiles.Tile(gid, {}, tile_image)
            
            gid += 1
            x += tile_width + spacing
        y -= tile_height + spacing

    return tiles


def load_tile_properties(tileset_node):
    """Fetches properties for tiles from a tileset. Returns a dictionary, where the keys are
    the tile IDs."""
    first_gid = int(tileset_node.getAttribute('firstgid'))
    tile_nodes = tileset_node.getElementsByTagName('tile')

    properties = {}

    for tile_node in tile_nodes:
        # The id attribute specifies a unique id for a tile PER TILESET. This is different
        # from the 'gid' attribute.
        gid = int(tile_node.getAttribute('id')) + first_gid
        properties[gid] = load_properties(tile_node)

    return properties


def load_properties(node):
    """Loads properties on a .tmx node into a dictionary. Checks for existence of
    a properties node. Returns an empty dictionary if no properties are available."""
    properties = {}

    if has_child(node, 'properties'):
        property_nodes = get_first(node, 'properties').getElementsByTagName('property')

        for property_node in property_nodes:
            name = property_node.getAttribute('name')
            value = property_node.getAttribute('value')
            properties[name] = value

    return properties


def create_gid_matrix(map_node):
    """Creates a column ordered bottom-up, left-right gid matrix by iterating over all
    the layers in the map file, overwriting all positions in the gid matrix for all non-empty
    tiles in each layer. This method also enforces that all tile spots in the final gid matrix
    are occupied. It raises a MapException if any tile locations are not occupied."""
    width = int(map_node.getAttribute('width'))
    height = int(map_node.getAttribute('height'))

    gid_matrix = create_empty_gid_matrix(width, height)

    layer_nodes = map_node.getElementsByTagName('layer')

    for layer_node in layer_nodes:
        tile_index = 0
        tile_nodes = get_first(layer_node, 'data').getElementsByTagName('tile')
        for row in gid_matrix:
            for col_index, col in enumerate(row):
                tile_node = tile_nodes[tile_index]
                gid = int(tile_node.getAttribute('gid'))
                if gid > 0:
                    row[col_index] = gid
                tile_index += 1

    if any([min(row) <= 0 for row in gid_matrix]):
        raise MapException('All tile locations should be occupied.')

    return rotate_matrix_ccw(gid_matrix)


def create_empty_gid_matrix(width, height):
    """Creates a matrix of the given size initialized with all zeroes."""
    return [[0] * width for row_index in range(height)]


def rotate_matrix_ccw(matrix):
    """Rotates a matrix 90 degrees counter-clockwise. This is used to turn tiled's left-right,
    top-bottom order into cocos' column based bottom-up, left-right order."""
    result = []
    for row in zip(*matrix):
        row = list(row)
        row.reverse()
        result.append(row)
    return result


def get_text_contents(node, preserve_whitespace=False):
    """Returns the text contents for a particular node. By default discards
    leading and trailing whitespace."""
    result = ''.join([node.data for node in node.childNodes if node.nodeType == node.TEXT_NODE])
    
    if not preserve_whitespace:
        result = result.strip()
    
    return result


def get_first(parent, tag_name):
    """Returns the parent's first child tag matching the tag name."""
    return parent.getElementsByTagName(tag_name)[0]


def try_attribute(node, attribute_name, default=None):
    """Tries to get an attribute from the supplied node. Returns the default
    value if the attribute is unavailable."""
    if node.hasAttribute(attribute_name):
        return node.getAttribute(attribute_name)
    
    return default


def has_child(node, child_tag_name):
    """Determines if the node has at least one child with the specified tag name."""
    return len(node.getElementsByTagName(child_tag_name)) > 0
