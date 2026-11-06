# Running cat

These four PNG files are copied byte-for-byte from
[zaeemali272/zenith-shell](https://github.com/zaeemali272/zenith-shell), revision
`ce18f9b9c13dc01e96749ca391d9fad05ec635ac`, `assets/cat_f0.png` through
`assets/cat_f3.png`. The NixOS repository links that shell in its Home Manager
configuration. Zenith Shell distributes these files under the Unlicense;
its license text is retained alongside them.

The frame order and original timings come from `bar/Right/Resources.qml` at that same
revision: balanced 150 ms, performance 80 ms, turbo 50 ms, powersave 220 ms,
and unknown profiles 200 ms. Our standard `power-saver` profile maps to powersave.
The original PNG dimensions and pixels are unchanged. `cat_strip.png` packs
the four originals side by side, with no resampling, for Qt's `AnimatedSprite`.
QML scales the sprite while preserving its aspect ratio, without blending poses.
Our playback uses 80 ms for balanced/unknown profiles, 60 ms for performance,
50 ms for turbo and 100 ms for powersave/power-saver. This keeps the cat running
even on power saver, instead of the original 220 ms pauses between poses.
The bar's global animation-off setting and hidden previews pause the animator.
No theme tint is applied to the artwork.

To regenerate the atlas with ImageMagick from this directory:

```sh
magick cat_f0.png cat_f1.png cat_f2.png cat_f3.png +append cat_strip.png
```
