#!/usr/bin/env python

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    import cocos
    import tiled2cocos

    cocos.director.director.init(width=600, height=600)

    test_map = tiled2cocos.load_map(os.path.join(os.path.dirname(__file__), 'data', 'map.tmx'))

    scroller = cocos.tiles.ScrollingManager()
    scroller.add(test_map)

    cocos.director.director.run(cocos.scene.Scene(test_map))
