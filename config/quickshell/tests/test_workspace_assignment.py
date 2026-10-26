"""Exercise fixed workspace ownership using a Lua compositor fixture."""
from pathlib import Path
import shutil
import subprocess
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'hypr/modules/workspaces.lua'


@unittest.skipUnless(shutil.which('lua'), 'Lua interpreter unavailable')
class WorkspaceAssignmentTests(unittest.TestCase):
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
