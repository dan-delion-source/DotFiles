#!/bin/bash

echo "🧹 Starting full system cleanup..."

# 1. Remove orphan packages
echo "➡ Removing orphan packages..."
orphans=$(pacman -Qtdq)
if [ -n "$orphans" ]; then
    sudo pacman -Rns --noconfirm $orphans
else
    echo "✔ No orphan packages found"
fi

# 2. Clean pacman cache (keep last 2 versions)
echo "➡ Cleaning pacman cache..."
sudo paccache -r -k 2

# 3. Full pacman cache clean (uncomment if you want aggressive)
# sudo pacman -Scc --noconfirm

# 4. Clean yay cache
echo "➡ Cleaning yay cache..."
yay -Sc --noconfirm

# 5. Remove unneeded dependencies (yay side)
echo "➡ Removing unused AUR dependencies..."
aur_orphans=$(yay -Qtdq)
if [ -n "$aur_orphans" ]; then
    yay -Rns --noconfirm $aur_orphans
else
    echo "✔ No AUR orphan packages"
fi

# 6. Clean journal logs (keep 7 days)
echo "➡ Cleaning journal logs..."
sudo journalctl --vacuum-time=7d

# 7. Remove trash files
echo "➡ Emptying trash..."
rm -rf ~/.local/share/Trash/*

# 8. Remove cache (SAFE partial clean)
echo "➡ Cleaning user cache..."
rm -rf ~/.cache/thumbnails/*

echo "✅ Cleanup complete!"
