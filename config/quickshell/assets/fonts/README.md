# Workspace Kanji font

`workspace-kanji.otf` is a 6 KB subset of Noto Sans JP Regular, covering
`一二三四五六七八九十`, ASCII digits, and space. Workspace styles other than
Kanji continue using the configured interface font. Qt loads this asset
locally; users do not need Japanese system fonts or a font-cache refresh.

Source: [Noto CJK](https://github.com/notofonts/noto-cjk), commit
`f8d157532fbfaeda587e826d4cd5b21a49186f7c`,
`Sans/SubsetOTF/JP/NotoSansJP-Regular.otf`.
Source SHA256: `dff723ba59d57d136764a04b9b2d03205544f7cd785a711442d6d2d085ac5073`.

Copyright © 2014–2021 Adobe (http://www.adobe.com/).
Distributed under the SIL Open Font License 1.1; see `OFL.txt`.
The subset's public family is renamed **DanShell Workspace Kanji**.
Copyright and license name records are retained in the font.

To rebuild from the exact upstream font, run:

```sh
python3 build_workspace_font.py /path/to/NotoSansJP-Regular.otf
```

This development-only step uses the system HarfBuzz subsetting library. The
installer simply copies the prebuilt subset with the rest of the config.
