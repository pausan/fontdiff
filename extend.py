#
# Takes a base font and a "model" font. It extends base font with glyphs from
# other files based on the font to model.
#
import os
import sys
import argparse
import shutil
import util
import time

def findFilesWithAllSymbols(font_files, symbols):
  """ Opens font files and finds all that fully contain given set of symbols
  """
  fonts_with_all_symbols = []
  for font_file in font_files:
    try:
      all_symbols = util.getSymbolIds(font_file)
      if (set(all_symbols) & set(symbols)) == set(symbols):
        fonts_with_all_symbols.append(font_file)
    except:
      pass
  return fonts_with_all_symbols

def main():
  parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    formatter_class=argparse.RawTextHelpFormatter,
    description="""
Analyze model font and extends base font with new glyphs from the rest of files provided
    """,
    epilog="""
Examples:
  # New font will be created from BaseFont.ttf with glyphs extra-*.ttf fonts in order
  # to match all glyphs/symbols present on FontToMatch.ttf
  $ python3 extend.py -m FontToMatch.ttf -b BaseFont.ttf extra-font1.ttf extra-font2.ttf ...
"""
  )

  parser.add_argument('--original', help="Original font where we'd like to match the symbols from")
  parser.add_argument('--base', help="Base font that we want to extend")
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('extra_fonts', nargs='+', help="Extra fonts that will be used to copy symbols to base")

  args = parser.parse_args()
  verbose = args.verbose

  base_font = args.base
  (base_font_name, base_font_ext) = os.path.splitext(os.path.basename(base_font))

  original_font = args.original
  (original_font_name, original_font_ext) = os.path.splitext(os.path.basename(original_font))

  extra_fonts = args.extra_fonts

  # place all output files in a new directory
  outdir = f"{base_font_name}-extended-{time.strftime('%Y-%m-%d_%H.%M.%S')}"
  os.makedirs(outdir)

  base_symbols = util.getSymbolIds(base_font)
  original_symbols = util.getSymbolIds(original_font)
  original_chars = [chr(c) for c in original_symbols]

  # Find symbols that are missing in the base font
  missing_codepoints = []
  for codepoint in original_symbols:
    if codepoint not in base_symbols:
      missing_codepoints.append (codepoint)

  if len(missing_codepoints) == 0:
    print("No missing symbols found! Font is already complete.")
    return

  print(f"{len(missing_codepoints)} missing symbols:")
  for codepoint in missing_codepoints:
    print(f"  Unicode hex: {codepoint:04x}")
  print("")

  # draw original matrix
  original_image = util.drawFullSymbolMatrix(original_chars, None, original_font, title=f"Font To Clone (org): {original_font}")
  original_image.save(f"{outdir}/{original_font_name}-matrix.png")

  fonts_with_all_symbols = findFilesWithAllSymbols(extra_fonts, missing_codepoints)
  for font_file in fonts_with_all_symbols:
    font_file_basename = os.path.splitext(os.path.basename(font_file))[0]
    new_font = f"{outdir}/{base_font_name}__from__{font_file_basename}{base_font_ext}"
    shutil.copy(base_font, new_font)

    if not util.copyFontGlyphs(
      base_font_file = new_font,
      from_font_file = font_file,
      target_font_file = new_font,
      glyph_codepoints = missing_codepoints
    ):
      print(f"Font {font_file} has all missing symbols, but we cannot copy!")
      os.unlink(new_font)
      continue

    print(f"Font {font_file} has all missing symbols. Creating {new_font}")
    image_matrix = util.drawFullSymbolMatrix(original_chars, None, new_font, title=f"{base_font} + {font_file_basename}")
    image_matrix.save(f"{outdir}/{base_font_name}__from__{font_file_basename}.png")

    gif = original_image.copy()
    gif.save(
      f"{outdir}/{base_font_name}__all_from__{font_file_basename}.gif",
      append_images=[image_matrix],
      save_all = True,
      duration = 1000,
      loop = 0
    )

  if len(fonts_with_all_symbols) > 0:
    return

  # if we haven't found a file with all symbols, we'll fill from multiple files
  print ("Will copy font symbols from multiple files!")
  new_font = f"{outdir}/{base_font_name}-multiple{base_font_ext}"
  shutil.copy(base_font, new_font)

  for extra_file in extra_fonts:
    if verbose:
      print (f"Analyzing file {extra_file} to find missing symbols...")
    extra_symbols = util.getSymbolIds(extra_file)

    found_codepoints = []
    for codepoint in missing_codepoints:
      if codepoint in extra_symbols:
        if verbose:
          print(f"  Symbol {codepoint:04x} found in {extra_file}...")
        found_codepoints.append(codepoint)

    if len(found_codepoints) > 0:
      if util.copyFontGlyphs(
        base_font_file=new_font,
        from_font_file=extra_file,
        target_font_file=new_font,
        glyph_codepoints = found_codepoints
      ):
        for codepoint in found_codepoints:
          print(f"  Imported symbol {codepoint:04x} from {extra_file} into {new_font}...")
          missing_codepoints.remove(codepoint)
    else:
      if sorted(missing_codepoints) == sorted(found_codepoints):
        print(f"  All missing symbols found in {extra_file}!")

    # no more symbols to find, we are done
    if len(missing_codepoints) == 0:
      break

  if len(missing_codepoints) != 0:
    print ("-"*80)
    print ("WARNING: Not all symbols have been added!! You'll need to add more fonts")
    print (f"WARNING: {len(missing_codepoints)} missing symbols!")
    print ("-"*80)
    print (f"Output files created here: {outdir}/")
    print ("-"*80)
    return
  else:
    print ("-"*80)
    print ("SUCCESS: All missing symbols have been filled in from other fonts!")
    print ("-"*80)
    print (f"Output files created here: {outdir}/")
    print ("-"*80)

  # the new image
  image_matrix = util.drawFullSymbolMatrix(
    original_chars,
    None,
    new_font,
    title=f"{base_font_name} extended with multiple fonts"
  )
  image_matrix.save(f"{outdir}/{base_font_name}-multiple.png")

  gif = original_image.copy()
  gif.save(
    f"{outdir}/{base_font_name}-all-multiple.gif",
    append_images=[image_matrix],
    save_all = True,
    duration = 1000,
    loop = 0
  )

  return


if __name__ == '__main__':
  main()
