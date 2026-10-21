-- Resolve this checkout's shell; never target all QuickShell instances.
local source = debug.getinfo(1, "S").source:sub(2)
local modules = source:match("^(.*)/[^/]+$")
assert(modules, "Cannot resolve shell module location")
local script = modules .. "/../../quickshell/scripts/shell-control.sh"
local quoted = "'" .. script:gsub("'", [['"'"']]) .. "'"
return { command = "sh " .. quoted }
