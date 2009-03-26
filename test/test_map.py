#!/usr/bin/env python

def test_property(obj, key, expected_value):
    assert key in obj.properties and obj.properties[key] == expected_value

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    import cocos
    import tiled2cocos

    cocos.director.director.init(width=600, height=600)

    test_map = tiled2cocos.load_map(os.path.join(os.path.dirname(__file__), 'data', 'map.tmx'))
    
    # Test properties
    gray_cell = test_map.get_cell(6, 8)
    test_property(test_map, 'creator', 'maikg')   
    test_property(gray_cell.tile, 'gray', 'yes')
    test_property(gray_cell.tile, 'boring', 'a bit')

    scroller = cocos.tiles.ScrollingManager()
    scroller.add(test_map)

    cocos.director.director.run(cocos.scene.Scene(test_map))
