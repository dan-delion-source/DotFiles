"""Exercise fixed workspace ownership using a Lua compositor fixture."""
from pathlib import Path
import shutil
import subprocess
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'hypr/modules/workspaces.lua'


@unittest.skipUnless(shutil.which('lua'), 'Lua interpreter unavailable')
class WorkspaceAssignmentTests(unittest.TestCase):
    def test_occupied_only_cycles_and_swipe_callbacks(self):
        script = '''
local laptop, hdmi = {name="eDP-1"}, {name="HDMI-A-5"}
local active, calls, gestures = nil, {}, {}
local workspaces = {}
for index=1,10 do
  workspaces[index] = {id=index, windows=0, monitor=index <= 5 and laptop or hdmi}
end
for _,index in ipairs({1,2,4,6,8,10}) do workspaces[index].windows=1 end
-- A scratchpad and another monitor's occupied workspace must not be selected.
table.insert(workspaces, {id=-99, windows=3, monitor=laptop})
table.insert(workspaces, {id=11, windows=1, monitor={name="DP-9"}})
hl = {
  get_monitors=function() return {laptop, hdmi} end,
  get_active_workspace=function() return active end,
  get_workspaces=function() return workspaces end,
  workspace_rule=function() end, on=function() end,
  dispatch=function(action) table.insert(calls, action.workspace) end,
  dsp={focus=function(args) return args end},
  config=function() end, plugin={},
  gesture=function(spec) gestures[spec.direction]=spec end,
}
local map = dofile(MODULE_PATH)
local function check(start, direction, expected, offer_empty)
  active = start and workspaces[start] or nil
  calls = {}
  map.cycle_used(direction, offer_empty)
  assert(#calls == (expected and 1 or 0), "wrong dispatch count from " .. tostring(start))
  if expected then assert(calls[1] == expected, tostring(start) .. " -> " .. tostring(calls[1])) end
end
check(1,1,2); check(2,1,4); check(4,1,1)
check(1,-1,4); check(4,-1,2); check(2,-1,1)
check(6,1,8); check(8,1,10); check(10,1,6)
check(6,-1,10); check(10,-1,8); check(8,-1,6)
check(3,1,4); check(3,-1,2); check(5,1,1); check(5,-1,4)
check(nil,1,nil); check(1,0,nil)
-- Swipes offer a single empty slot, skip gaps, and wrap if it stays unused.
check(1,1,2,true); check(2,1,4,true); check(4,1,5,true)
check(5,1,1,true); check(5,-1,4,true)
workspaces[5].windows=1
check(4,1,5,true)
-- At the end of this monitor's range, reuse an earlier free slot, not HDMI.
check(5,1,3,true); check(3,1,1,true)
workspaces[3].windows=1
check(5,1,1,true) -- full monitor: wrap immediately
workspaces[3].windows=0; workspaces[5].windows=0
check(10,1,7,true); check(7,1,6,true); check(9,-1,8,true)
-- The wheel still wraps immediately, even when a free slot is available.
check(4,1,1); check(10,1,6)
-- Closing a window removes that workspace from the next cycle immediately.
workspaces[2].windows=0
check(1,1,4)
workspaces[4].windows=0
check(1,1,nil); check(3,-1,1)
workspaces[1].windows=0
check(1,1,nil); check(3,-1,nil)
check(1,1,nil,true)
workspaces[1].monitor=nil
check(1,1,nil)
workspaces[1].monitor=laptop
-- When HDMI is unplugged, its rehomed workspaces cycle on the laptop too.
for index=6,10 do workspaces[index].monitor=laptop end
check(3,1,6); check(6,-1,10)
-- Execute the same callbacks that Hyprland registers for physical swipes.
package.loaded["modules.workspaces"] = map
dofile(INPUT_PATH)
assert(gestures.horizontal == nil)
assert(gestures.left.fingers == 3 and gestures.right.fingers == 3)
active = workspaces[6]; calls = {}
gestures.left.action(); assert(calls[1] == 8)
calls = {}; gestures.right.action(); assert(calls[1] == 10)
active = workspaces[10]; calls = {}
gestures.left.action(); assert(calls[1] == 1)
active = workspaces[1]; calls = {}
gestures.left.action(); assert(calls[1] == 6)
print("OCCUPIED_WORKSPACE_CYCLING_OK")
'''
        script = ('MODULE_PATH = ' + repr(str(MODULE)) + '\nINPUT_PATH = '
                  + repr(str(MODULE.with_name('input.lua'))) + '\n' + script)
        result = subprocess.run(['lua', '-'], input=script, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OCCUPIED_WORKSPACE_CYCLING_OK', result.stdout)

    def test_fixed_ranges_focus_move_and_hotplug_fallback(self):
        script = '''
local monitors = {{name="eDP-1"}, {name="HDMI-A-5"}}
local workspaces = {{id=1, monitor={name="HDMI-A-5"}}, {id=6, monitor={name="eDP-1"}},
                    {id=-1, monitor={name="eDP-1"}}}
local rules, events, calls = {}, {}, {}
hl = {
  get_monitors=function() return monitors end,
  get_workspaces=function() return workspaces end,
  workspace_rule=function(rule) table.insert(rules, rule) end,
  on=function(name, callback) events[name]=callback end,
  dispatch=function(action) table.insert(calls, action) end,
  dsp={focus=function(args) return {kind="focus", args=args} end,
       window={move=function(args) return {kind="window", args=args} end},
       workspace={move=function(args) return {kind="workspace", args=args} end}},
}
local map = dofile(MODULE_PATH)
assert(#rules == 10)
for index=1,10 do
  assert(rules[index].workspace == tostring(index))
  assert(rules[index].monitor == (index <= 5 and "eDP-1" or "HDMI-A-5"))
  assert(rules[index].persistent)
  assert(map.monitor_for(index) == rules[index].monitor)
  map.focus(index)
  assert(calls[#calls].kind == "focus" and calls[#calls].args.workspace == index)
  assert(calls[#calls].args.on_current_monitor == nil)
  map.move_window(index)
  assert(calls[#calls].kind == "window" and calls[#calls].args.workspace == index)
end
calls = {}
events["config.reloaded"]()
assert(#calls == 2)
assert(calls[1].args.monitor == "eDP-1" and calls[2].args.monitor == "HDMI-A-5")
monitors = {{name="eDP-1"}}
assert(map.monitor_for(6) == "eDP-1")
monitors = {{name="DP-9"}}
assert(map.monitor_for(1) == "DP-9" and map.monitor_for(10) == "DP-9")
monitors = {}
assert(map.monitor_for(1) == nil and map.monitor_for(-1) == nil)
print("WORKSPACE_ASSIGNMENTS_OK")
'''
        script = 'MODULE_PATH = ' + repr(str(MODULE)) + '\n' + script
        result = subprocess.run(['lua', '-'], input=script, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('WORKSPACE_ASSIGNMENTS_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
