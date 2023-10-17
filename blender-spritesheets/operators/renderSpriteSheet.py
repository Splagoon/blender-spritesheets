import os
import sys
import bpy
import math
import mathutils
import shutil
import platform
import subprocess
import json
from properties.SpriteSheetPropertyGroup import SpriteSheetPropertyGroup
from properties.ProgressPropertyGroup import ProgressPropertyGroup

platform = platform.system()
if platform == "Windows":
    ASSEMBLER_FILENAME = "assembler.exe"
elif platform == "Linux":
    ASSEMBLER_FILENAME = "assembler_linux"
else:
    ASSEMBLER_FILENAME = "assembler_mac"


class RenderSpriteSheet(bpy.types.Operator):
    """Operator used to render sprite sheets for an object"""

    bl_idname = "spritesheets.render"
    bl_label = "Render Sprite Sheets"
    bl_description = "Renders all actions to a single sprite sheet"

    def execute(self, context):
        scene = bpy.context.scene
        props = scene.SpriteSheetPropertyGroup
        progressProps = scene.ProgressPropertyGroup
        progressProps.rendering = True
        progressProps.success = False
        progressProps.actionTotal = len(bpy.data.actions)

        animation_descs = []
        frame_end = 0

        objectToRender = props.target
        cameraRoot = props.cameraRoot
        for angleIdx in range(8):
            angle = angleIdx * 45
            progressProps.angle = angle
            cameraRoot.rotation_euler = mathutils.Euler(
                (0.0, 0.0, math.radians(angle)), "XYZ"
            )

            for index, action in enumerate(bpy.data.actions):
                loop = action.name.endswith("_loop")
                action_name = action.name
                if loop:
                    action_name = action.name[:-5]
                progressProps.actionName = action_name
                progressProps.actionIndex = index
                objectToRender.animation_data.action = action

                _, frameMin, frameMax = frame_count(action.frame_range)
                frames = []
                durations = []
                if (
                    props.onlyRenderMarkedFrames is True
                    and action.pose_markers is not None
                    and len(action.pose_markers.keys()) > 0
                ):
                    pose_frames = sorted(
                        map(lambda p: p.frame, action.pose_markers.values())
                    )
                    for i in range(len(pose_frames)):
                        marker = pose_frames[i]
                        next_marker = frameMax
                        if i + 1 < len(pose_frames):
                            next_marker = pose_frames[i + 1]
                        durations.append(math.ceil(next_marker - marker))
                        frames.append(marker)
                else:
                    durations.append(1)
                    frames = range(frameMin, frameMax + 1)

                frame_end += len(frames)
                animation_descs.append(
                    {
                        "angle": angle,
                        "name": action_name,
                        "end": frame_end,
                        "frame_durations": durations,
                        "loop": loop,
                    }
                )

                self.processAction(
                    action, scene, props, progressProps, objectToRender, frames
                )

        assemblerPath = os.path.normpath(
            os.path.join(
                props.binPath,
                ASSEMBLER_FILENAME,
            )
        )
        print("Assembler path: ", assemblerPath)
        subprocess.run(
            [
                assemblerPath,
                "--root",
                bpy.path.abspath(props.outputPath),
                "--out",
                objectToRender.name + ".png",
            ]
        )

        json_info = {
            "name": objectToRender.name,
            "tileWidth": props.tileSize[0],
            "tileHeight": props.tileSize[1],
            "frameRate": props.fps,
            "animations": animation_descs,
        }

        with open(
            bpy.path.abspath(
                os.path.join(props.outputPath, objectToRender.name + ".bss")
            ),
            "w",
        ) as f:
            json.dump(json_info, f, indent="\t")

        progressProps.rendering = False
        progressProps.success = True
        shutil.rmtree(bpy.path.abspath(os.path.join(props.outputPath, "temp")))
        return {"FINISHED"}

    def processAction(
        self, action, scene, props, progressProps, objectToRender, frames
    ):
        """Processes a single action by iterating through each frame and rendering tiles to a temp folder"""
        frameRange = action.frame_range
        frameCount, _, _ = frame_count(frameRange)
        progressProps.tileTotal = frameCount
        for frame in frames:
            progressProps.tileIndex = frame
            scene.frame_set(frame)
            # TODO: Unfortunately Blender's rendering happens on the same thread as the UI and freezes it while running,
            # eventually they may fix this and then we can leverage some of the progress information we track
            bpy.ops.spritesheets.render_tile("EXEC_DEFAULT")


def frame_count(frame_range):
    frameMin = math.floor(frame_range[0])
    frameMax = math.ceil(frame_range[1])
    return (frameMax - frameMin, frameMin, frameMax)
