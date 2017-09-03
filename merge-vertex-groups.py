# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Merge Vertex Groups",
    "description": "Merge Vertex Groups",
    "author": "Christian Brinkmann, Paul Gee",
    "version": (0, 1, 0),
    "blender": (2, 76, 0),
    "location": "Properties > Object Data > Vertex Groups",
    "tracker_url": "",
    "category": "Mesh"
}

import bpy
import random

from bpy.props import (IntProperty,
                       BoolProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty
                       )

from bpy.types import (Operator,
                       UIList,
                       PropertyGroup
                       )




# -------------------------------------------------------------------
# Properties    
# -------------------------------------------------------------------

class MvgSettings(PropertyGroup):

    uilist_index = IntProperty()
    merge_vgroups = BoolProperty(default=False)


class MvgPropertyCollection(PropertyGroup):
    
    collection_id = IntProperty()


# -------------------------------------------------------------------
# Vertex Group Operators    
# -------------------------------------------------------------------

class MergeVertexGroupUiList(Operator):
    bl_idname = "mesh.merge_vg_ui_list"
    bl_label = "Merge Groups"
    bl_description = "Merge all Groups in List"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object.type == 'MESH' and 
            context.mode == 'OBJECT' and
            len(context.active_object.vertex_groups) > 1)
    
    def execute(self, context):
        group_input = {i.name for i in context.scene.merge_vertex_groups_collection if i.name}
        ob = bpy.context.active_object

        group_lookup = {g.index: g.name for g in ob.vertex_groups}
        group_candidates = {n for n in group_lookup.values() if n in group_input}
        
        if len(group_candidates) > 1:
            # iterate through the vertices and sum the weights per group
            vertex_weights = {}
            for vert in ob.data.vertices:
                if len(vert.groups):  
                    for item in vert.groups:
                        vg = ob.vertex_groups[item.group]
                        if vg.name in group_candidates:
                            if vert.index in vertex_weights:    
                                vertex_weights[vert.index] += vg.weight(vert.index)
                            else:
                                vertex_weights[vert.index] = vg.weight(vert.index)
                        
            # create new vertex group
            vgroup = ob.vertex_groups.new(name="+".join(group_candidates))
            
            # add the values to the group                       
            for key, value in vertex_weights.items():
                vgroup.add([key], value ,'REPLACE') #'ADD','SUBTRACT'
            
            self.report({'INFO'}, ('Merged: %s' % (', '.join(group_candidates))))
            return{'FINISHED'}
        
        else:
            self.report({'WARNING'}, "No Groups to merge.")
            return{'CANCELLED'}


class PrintVertexGroupUiList(Operator):
    bl_idname = "mesh.print_vg_ui_list"
    bl_label = "Print Selection"
    bl_description = "Print Vertex Group Selection to Console"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        selection = {i.name for i in context.scene.merge_vertex_groups_collection if i.name}
        if selection:
            self.report({'INFO'}, ", ".join(selection)) 
        else:
            self.report({'INFO'}, "Nothing in Selection")
        return{'FINISHED'}


class AddAllGroupsToUiList(Operator):
    bl_idname = "mesh.add_all_vg_ui_list"
    bl_label = "Add All Groups"
    bl_description = "Add all Vertex Groups to the List"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        mvg = scn.merge_vertex_groups
        colprop = scn.merge_vertex_groups_collection
        idx = mvg.uilist_index
                    
        try:
            item = colprop[idx]
        except IndexError:
            pass
        
        for idx, item in enumerate(colprop):
            if not item.name:
                colprop.remove(idx)
                
        items = 0
        for g in context.active_object.vertex_groups:
            if g.name not in scn.merge_vertex_groups_collection:
                item = colprop.add()
                item.collection_id = len(colprop)
                item.name = g.name
                mvg.uilist_index = (len(colprop)-1)
                items += 1
        
        if items: info = '%s Vertex Groups added to the list' % (items)
        else: info = 'Nothing to add'
        self.report({'INFO'}, info)
        return{'FINISHED'}


class ClearVertexGroupUiList(Operator):
    bl_idname = "mesh.clear_vg_ui_list"
    bl_label = "Clear List"
    bl_description = "Clear all Items in Vertex Group list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        mvg = scn.merge_vertex_groups
        coll = scn.merge_vertex_groups_collection
                
        if len(coll) > 0:
             # reverse range to remove last item first
            for i in range(len(coll)-1,-1,-1):
                coll.remove(i)
            self.report({'INFO'}, "All items removed")
        else:
            self.report({'INFO'}, "Nothing to remove")   
        return{'FINISHED'}


# -------------------------------------------------------------------
# Ui
# -------------------------------------------------------------------

class ActionsVertexGroupUiList(Operator):
    bl_idname = "mesh.action_vg_ui_list"
    bl_label = "Vertex Group List Actions"
    bl_options = {'REGISTER', 'UNDO'}

    action = EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
        )
    )

    def invoke(self, context, event):
        scn = context.scene
        mvg = scn.merge_vertex_groups
        colprop = scn.merge_vertex_groups_collection
        idx = mvg.uilist_index

        try:
            item = colprop[idx]
        except IndexError:
            pass

        else:
            if self.action == 'DOWN' and idx < len(colprop) - 1:
                item_next = colprop[idx+1].name
                mvg.uilist_index += 1
                info = 'Item %d selected' % (mvg.uilist_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                item_prev = colprop[idx-1].name
                mvg.uilist_index -= 1
                info = 'Item %d selected' % (mvg.uilist_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                            
                first_item = True if mvg.uilist_index == 0 else False
                
                if colprop[mvg.uilist_index].name:
                    info = '%s removed from list' % (colprop[mvg.uilist_index].name)
                else:
                    info = 'Item %s removed from list' % (mvg.uilist_index +1)
                
                if first_item:
                    mvg.uilist_index = 0
                else:
                    mvg.uilist_index -= 1
                
                self.report({'INFO'}, info)
                colprop.remove(idx)

        if self.action == 'ADD':
            item = colprop.add()
            item.collection_id = len(colprop)
            mvg.uilist_index = (len(colprop)-1)

        return {"FINISHED"}


class VertexGroupUiList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(.1)
        split.scale_y = 1.1
        split.label(str(index+1))
        split.prop_search(item, "name", context.active_object, "vertex_groups", text="")


def vertexgroup_panel_append(self, context):
        
    if (context.active_object.type == 'MESH' and 
        len(context.active_object.vertex_groups) > 1 and
        context.mode == 'OBJECT'):
        
        scn = context.scene
        mvg = scn.merge_vertex_groups
        layout = self.layout

        box_merge_vgroups = layout.box()
        row = box_merge_vgroups.row()
        row.prop(mvg, "merge_vgroups",
            icon="TRIA_DOWN" if mvg.merge_vgroups else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        row.label(text="Merge Vertex Groups")
        if mvg.merge_vgroups:

            rows = 4
            row = box_merge_vgroups.row() 
            row.template_list("VertexGroupUiList", "", scn, "merge_vertex_groups_collection", mvg, "uilist_index", rows=rows)
            
            col = row.column(align=True)
            col.operator("mesh.action_vg_ui_list", icon='ZOOMIN', text="").action = 'ADD'
            col.operator("mesh.action_vg_ui_list", icon='ZOOMOUT', text="").action = 'REMOVE'
            col.separator()
            col.operator("mesh.action_vg_ui_list", icon='TRIA_UP', text="").action = 'UP'
            col.operator("mesh.action_vg_ui_list", icon='TRIA_DOWN', text="").action = 'DOWN'

            row = box_merge_vgroups.row()
            col = row.column(align=True)
            rowsub = col.row(align=True)
            #rowsub.operator("mesh.print_vg_ui_list", icon="WORDWRAP_ON")
            rowsub.operator("mesh.add_all_vg_ui_list", icon="WORDWRAP_ON")
            rowsub.operator("mesh.clear_vg_ui_list", icon="X")
            col.operator("mesh.merge_vg_ui_list", icon="STICKY_UVS_LOC")

        layout.separator()


# -------------------------------------------------------------------
# Register
# -------------------------------------------------------------------

def register():
    bpy.utils.register_module(__name__)
    bpy.types.DATA_PT_vertex_groups.append(vertexgroup_panel_append)
    bpy.types.Scene.merge_vertex_groups = PointerProperty(type=MvgSettings)
    bpy.types.Scene.merge_vertex_groups_collection = CollectionProperty(type=MvgPropertyCollection)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.DATA_PT_vertex_groups.remove(vertexgroup_panel_append)
    del bpy.types.Scene.merge_vertex_groups_collection
    del bpy.types.Scene.merge_vertex_groups

if __name__ == "__main__":
    register()
