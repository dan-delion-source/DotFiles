# Path
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"


plugins=(
  git
)



# -----------------------------
# FZF
# -----------------------------
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border=rounded --cycle --wrap"
export FZF_CTRL_T_COMMAND="eza --icons"
export FZF_CTRL_T_OPTS="--accept-nth=2"
export FZF_CTRL_R_OPTS="--with-nth=2,-1"

# -----------------------------
# ZOXIDE (z command)
# -----------------------------
if command -v zoxide >/dev/null; then
  eval "$(zoxide init zsh)"
fi

# -----------------------------
# Syntax Highlighting
# -----------------------------
if [ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]; then
  source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

# -----------------------------
# Autosuggestions
# -----------------------------
if [ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]; then
  source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#3E424A'
fi

# -----------------------------
# Completion Colors
# -----------------------------
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"

# -----------------------------
# Editor
# -----------------------------
export EDITOR=nvim
export MANPAGER='nvim +Man!'

# -----------------------------
# Aliases
# -----------------------------
if command -v eza >/dev/null; then
  alias ls='eza -h --git --icons'
  alias ll='eza -lah --git --icons'
  alias lt='eza --tree --icons'
fi

alias grep='grep --color=auto'
alias q='exit'

# Git shortcuts
alias gac='git add . && git commit -m'

# Cargo shortcuts
alias cb='cargo build'
alias cr='cargo run'

# -----------------------------
# Prompt (Clean Minimal)
# -----------------------------
autoload -Uz vcs_info
precmd() { vcs_info }

zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:git:*' formats '(%b)'

setopt prompt_subst

PS1="%B%F{#78B892}%n@%m %F{#79AAEB}%~ %F{#C488EC}${vcs_info_msg_0_} ❯ %f%b "

# -----------------------------
# Misc
# -----------------------------
export RUSTC_WRAPPER=sccache



# Run fastfetch on terminal start
if command -v fastfetch >/dev/null; then
  fastfetch
fi
