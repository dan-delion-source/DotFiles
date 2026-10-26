# Running cat

These four PNG files are copied byte-for-byte from
[zaeemali272/zenith-shell](https://github.com/zaeemali272/zenith-shell), revision
`ce18f9b9c13dc01e96749ca391d9fad05ec635ac`, `assets/cat_f0.png` through
`assets/cat_f3.png`. The NixOS repository links that shell in its Home Manager
configuration. Zenith Shell distributes these files under the Unlicense;
its license text is retained alongside them.

The frame order and timings come from `bar/Right/Resources.qml` at that same
revision: balanced 150 ms, performance 80 ms, turbo 50 ms, powersave 220 ms,
and unknown profiles 200 ms. Our standard `power-saver` profile maps to powersave.
The original PNG dimensions and pixels are unchanged; QML scales them while
preserving their aspect ratio. The bar's global animation-off setting pauses
the animator. No theme tint is applied to the artwork.
