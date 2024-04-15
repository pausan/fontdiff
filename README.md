# Font Tools

This project contains some font utilities created to analyze and compare
symbols/glyphs between different font files.

As an example, you have "extend.py" script which, given an "original" font,
a "base" font, and a list of "extra" fonts, will try to assess whether all
characters from original are on the base, and if not, will extend the base
font with those extra characters from the extra files provided.

It will:

- Tell you which characters are missing from the **base** that were available
  in the **original** font

- Explore all the **extra** fonts provided and try to find fonts that provide
  all those missing characters

   - If not, it will just pick characters from all the different fonts in the
     order provided

- Extend the **base** font with those new characters from the **extra** fonts
  and create a **ttf/otf** font and a couple of png/gifs to display the new
  font compared to the existing one in a matrix containing all symbols.

Example:

```bash
  $ python extend.py -v --original font1.ttf --base font2.ttf google-fonts/*.ttf
```

Feel free to run all the other scripts with -h to see the help.

## Installation

```bash
  $ python -m pip install -r requirements.txt
```
