#!/usr/bin/env python

def test_property(obj, key, expected_value):
    assert key in obj.properties and obj.properties[key] == expected_value

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    import pyglet.window.key
    import cocos
    import tiled2cocos
    
    from cocos.director import director
    from cocos.scenes import transitions

    director.init(width=600, height=600)
    
    scenes = []
    
    map_files = ['map.tmx', 'encoded.tmx', 'gzipped.tmx']
    
    for map_file in map_files:
        test_map = tiled2cocos.load_map(os.path.join(os.path.dirname(__file__), 'data', map_file))

        # Test properties
        gray_cell = test_map.get_cell(6, 8)
        test_property(test_map, 'creator', 'maikg')   
        test_property(gray_cell.tile, 'gray', 'yes')
        test_property(gray_cell.tile, 'boring', 'a bit')
        
        scroller = cocos.tiles.ScrollingManager()
        scroller.add(test_map)
        
        scenes.append(cocos.scene.Scene(test_map))
    
    scene_index = 0
    director.window.set_caption('tiled2cocos test [%s]' % (map_files[scene_index],))
    
    def on_key_press(symbol, modifiers):
        global scene_index, map_files
        if symbol == pyglet.window.key.SPACE:
            scene_index += 1
            if scene_index >= len(scenes):
                scene_index = 0
            director.replace(transitions.FlipX3DTransition(scenes[scene_index], duration=1))
            director.window.set_caption('tiled2cocos test [%s]' % (map_files[scene_index],))
    director.window.push_handlers(on_key_press)

    director.run(scenes[scene_index])
