@tool
extends EditorImportPlugin


func _get_importer_name():
	return "godot-bss-importer"


func _get_visible_name():
	return "SpriteFrames"


func _get_recognized_extensions():
	return ["bss"]


func _get_save_extension():
	return "tres"


func _get_resource_type():
	return "SpriteFrames"


func _get_preset_count():
	return 1


func _get_preset_name(preset):
	return "Default"


func _get_import_options(_path, preset):
	return [
		{
			"name": "sheet_image",
			"default_value": "",
			"property_hint": PROPERTY_HINT_FILE,
			"hint_string": "*.png",
			"tooltip": "Absolute path to the spritesheet .png."
		},
	]


func _get_option_visibility(_path, _option, _options):
	return true


func _get_priority():
	return 1.0


func _get_import_order():
	# After textures (0) but before scenes (100)
	return 50


func _import(source_file, save_path, options, platform_variants, gen_files):
	var file := FileAccess.open(source_file, FileAccess.READ)
	if file == null:
		printerr("Failed to open file: ", FileAccess.get_open_error())
		return FileAccess.get_open_error()

	var content = file.get_as_text()
	var data = JSON.parse_string(content)
	file.close()

	var texture = load(options["sheet_image"])
	if not texture:
		return OK

	var x_tiles = int(texture.get_width() / data["tileWidth"])
	var sprite_frames = SpriteFrames.new()

	var count = 0
	for anim_data in data["animations"]:
		var anim_name = "%s_%d" % [anim_data["name"], anim_data["angle"]]
		sprite_frames.add_animation(anim_name)
		sprite_frames.set_animation_speed(anim_name, data["frameRate"])

		for duration in anim_data["frame_durations"]:
			var atlas_texture = AtlasTexture.new()
			var x = count % x_tiles
			var y = count / x_tiles
			print_debug("tile: (%d, %d)" % [x, y])
			atlas_texture.atlas = texture
			atlas_texture.region = Rect2(
				x * data["tileWidth"], y * data["tileHeight"], data["tileWidth"], data["tileHeight"]
			)
			sprite_frames.add_frame(anim_name, atlas_texture, duration)
			count += 1

		# count = anim_data["end"]

	var filename = save_path + "." + _get_save_extension()
	var err = ResourceSaver.save(sprite_frames, filename)
	if err != OK:
		printerr("Failed to save resource: ", err)
		return err

	return OK
