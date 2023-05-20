
# python3-pillow python3-fonttools
# https://en.wikipedia.org/wiki/Adobe_Glyph_List
#
# Glyph names might be different on different fonts,
# but the IDs should match (e.g U+00A0 = nbspace = uni00A0)
#
# In this file we use Symbol instead of Glyph
#
#
# - Google Fonts by license
#   - git@github.com:google/fonts.git
#   - https://github.com/google/fonts/archive/main.zip
#
# - FontSource repo of open source fonts
#   https://github.com/fontsource/fontsource
#
# Licenses that can be used commercially:
#  - Apache License v2
#  - SIL Open Font License
#  - Ubuntu Font License
#
# More info: https://developers.google.com/fonts/faq?hl=en
#
# https://www.theleagueofmoveabletype.com/  -- gh
# https://fontlibrary.org/
# https://fontsource.org/
# https://github.com/fontsource/fontsource/tree/main/fonts
#
import math
import sys
import os
import time
import glob
import json
import argparse
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageSequence
from fontTools import ttLib
import numpy
import util

# ------------------------------------------------------------------------------
# Symbol IDs cache
# ------------------------------------------------------------------------------
STANDARD_ALPHABET = 'abcçdefghijklmnñopqrstuvwxyzABCÇDEFGHIJKLMNÑOPQRSTUVWXYZ01234567890!=.,-+*/%$&€áéíóúäëïöü'

def compareFonts(
  font_path1,
  font_path2,
  xoffset = 0,
  yoffset = 0,
  file_prefix = "",
  alphabet = None
):
  symbols1 = util.getSymbolIds(font_path1)
  symbols2 = util.getSymbolIds(font_path2)
  symbols3 = list(symbols1 | symbols2)

  size = math.ceil(len(symbols3)**0.5)

  codepoints = []
  codepoints_shared = []
  codepoints_missing_from2 = []
  for codepoint in sorted(symbols3):
    codepoints.append (chr(codepoint))

    if codepoint in symbols1 and codepoint in symbols2:
      codepoints_shared.append (chr(codepoint))

    if codepoint not in symbols2:
      codepoints_missing_from2.append (chr(codepoint))
    else:
      codepoints_missing_from2.append (' ')

  # to speedup the process we compare only a subset, if requested
  if alphabet:
    # codepoints_shared=codepoints_shared[0:max_items_to_compare]
    codepoints_shared = [x for x in codepoints_shared if x in alphabet]

  shared_size = math.ceil(len(codepoints_shared)**0.5)

  (sim_score, diff) = getFontDiffScore(
    codepoints_shared,
    shared_size,
    font_path1,
    font_path2,
    xoffset = xoffset,
    yoffset = yoffset
  )

  font1_base = os.path.basename(font_path1)
  font2_base = os.path.basename(font_path2)

  # if diff.getbbox() is not None:
  image1 = util.drawSymbolMatrix(
    codepoints,
    size,
    font_path1,
    title=font1_base
  )
  image2 = util.drawSymbolMatrix(
    codepoints,
    size,
    font_path2,
    title=f"{font2_base} with offset {xoffset}, {yoffset}",
    xoffset = xoffset,
    yoffset = yoffset
  )
  image_missing = util.drawSymbolMatrix(
    codepoints_missing_from2,
    size,
    font_path1,
    title=f"{len(symbols1 - symbols2)} {font1_base} chars not in {font2_base}"
  )

  image1.save(f"{file_prefix}_font1.png")
  image2.save(f"{file_prefix}_font2.png")
  image_missing.save(f"{file_prefix}3_missing.png")
  # diff.save(f"{file_prefix}_diff.png")

  return (sim_score, diff)

def getFontDiffScore(
  codepoints_shared,
  size,
  font_path1,
  font_path2,
  xoffset,
  yoffset
):
  """ Compute diff score between two images
  """
  im1 = util.drawSymbolMatrix(codepoints_shared, size, font_path1)
  im2 = util.drawSymbolMatrix(codepoints_shared, size, font_path2, xoffset = xoffset, yoffset = yoffset)

  diff = ImageChops.difference(im1, im2)
  #histogram = diff.histogram()

  # we can also try to minimize this:
  #sim_score = 1/sum(h * (i**2) for i, h in enumerate(histogram)) / (float(im1.size[0]) * im1.size[1])

  # 1/LOG(MSE) since we want to maximize
  diff = diff.convert("L")
  mse = numpy.mean(numpy.array(diff)) ** 2
  sim_score= 1/math.log(mse)

  #sim_score = histogram[0] / (float(im1.size[0]) * im1.size[1])
  return (sim_score, diff)

def fastSearchBestAlignment (
  font_path1,
  font_path2,
  step = 2,
  search_space = 12,
  x = 0,
  y = 0
):
  """ Quickly render a predefined string in a small grid to try to find
  a good alignment without having to render all similar simbols; this way, while
  less accurate, might help rendering simbols and finding similarities much
  faster
  """
  best_score = 0
  best_x = 0
  best_y = 0

  # this way we can explore a lot in very little time
  bbox = search_space
  for xoffset in range(x-bbox, x+bbox, step):
    for yoffset in range(y-bbox, y+bbox, step):
      (sim_score, _) = getFontDiffScore(
        'abjsAWM15', # 9 random letters - typical that are written different
        3,           # 3x3 grid
        font_path1,
        font_path2,
        xoffset,
        yoffset
      )
      if sim_score > best_score:
        best_score = sim_score
        best_x = xoffset
        best_y = yoffset

  return (best_x, best_y, best_score)

def searchBestAlignment(font_path1, font_path2, search_space = 1):
  """ Brute force search of any x/y axis to see how to match the font in the
  best possible way to previous one.
  """
  (best_x, best_y, best_score) = fastSearchBestAlignment(font_path1, font_path2, step = 4)
  (best_x, best_y, best_score) = fastSearchBestAlignment(font_path1, font_path2, step = 2, search_space = 4, x = best_x, y = best_y)

  symbols1 = util.getSymbolIds(font_path1)
  symbols2 = util.getSymbolIds(font_path2)

  codepoints_shared = [ chr(c) for c in sorted(symbols1 & symbols2)]
  size = math.ceil(len(codepoints_shared)**0.5)

  # NOTE: increasing bbox might find a better
  bbox = search_space
  total_search_space = (2*bbox)**2

  # brute force search
  for i, xoffset in enumerate(range(best_x-bbox, best_x+bbox)):
    for j, yoffset in enumerate(range(best_y-bbox, best_y+bbox)):
      n = i*(2*bbox) + j + 1
      sys.stdout.write (f"\r[{n:2d}/{total_search_space:2d}] Best offsets found ({best_x}, {best_y}, score={best_score:.3f})               ")
      sys.stdout.flush()

      (sim_score, _) = getFontDiffScore(
        codepoints_shared,
        size,
        font_path1,
        font_path2,
        xoffset,
        yoffset
      )

      if best_score is None or sim_score > best_score:
        best_score = sim_score
        best_x = xoffset
        best_y = yoffset

  print("")
  return (best_x, best_y, best_score)

def main():
  parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    formatter_class=argparse.RawTextHelpFormatter,
    description="""
Analyze font and try to find a similar one
    """,
    epilog="""
Examples:
  $ python3 fontdiff.py -b -v FontName.ttf google-fonts
  $ python3 fontdiff.py --fast-search -d cmpdir -b -v path/to/Font.ttf folder/containing/fonts
    """
  )

  parser.add_argument('-a', '--alphabet', help="Specify which letters should we try to match for scoring")
  parser.add_argument('--fast-search', action='store_true', help="Fast exploration to skip expensive comparisons (implies -b)")
  parser.add_argument('-b', '--best-fit', action='store_true', help="On each font, try to find the best fit")
  parser.add_argument('-d', '--out-dir', help="Output folder where images/diffs/etc will be generated")
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('input_font')
  parser.add_argument('font_search_path')

  args = parser.parse_args()

  verbose = args.verbose

  alphabet = args.alphabet
  if args.alphabet in ["std", "standard"]:
    alphabet = STANDARD_ALPHABET

  # if we want fast search we should go for best_fit for sure
  if args.fast_search:
    args.best_fit = True
  args.exhaustive_search = not args.fast_search

  if not args.out_dir:
    out_hash = getFileMd5(args.input_font)
    out_dir = os.path.split(os.path.splitext(args.input_font)[0])[1]
    args.out_dir = f'tmp-diff-{out_dir}-{out_hash[0:8]}'.lower()

  diff_folder = args.out_dir
  os.makedirs(diff_folder, exist_ok=True)

  util.init()

  font1 = args.input_font
  if os.path.isfile(args.font_search_path):
    font_files = [args.font_search_path]

  else:
    root_dir = args.font_search_path
    ttf_files = list(glob.glob('**/*.ttf', root_dir = root_dir, recursive = True))
    otf_files = list(glob.glob('**/*.otf', root_dir = root_dir, recursive = True))
    font_files = ttf_files + otf_files
    font_files = [os.path.join(root_dir, file) for file in font_files]

  # extract copyright/license/...
  # font = ttLib.TTFont(font2)
  # for record in font["name"].names:
  #   print(record)

  script_start_time = time.time()
  with open(f"{diff_folder}/analysis.txt", "wt") as f:
    symbols1 = util.getSymbolIds(font1)

    util.log(f, f"Finding best match for: {font1:<32}")
    util.log(f, f"{font1:<32}: {len(symbols1)} glyphs")
    matches = []

    top_score = 0
    for idx, ttf_file in enumerate(font_files):
      font2 = ttf_file
      try:

        start_time = time.time()
        util.log(f, f"\n[{idx+1}/{len(font_files)}] {font2}")

        prefix = os.path.splitext(os.path.basename(font2))[0].lower()
        symbols2 = util.getSymbolIds(font2)
        util.log(f, f"  {'Total glyps':<32}: {len(symbols1 | symbols2)} glyphs on both fonts")
        util.log(f, f"  {os.path.basename(font2):<32}: {len(symbols2)} glyphs (vs {len(symbols1)})")
        util.log(f, f"  {os.path.basename(font2):<32}: {len(symbols1&symbols2)} glyphs shared with {font1} (vs {len(symbols1)})")
        util.log(f, f"  {os.path.basename(font2):<32}: {len(symbols1-symbols2)} glyphs missing from {font1}")

        diff_len = len(symbols1-symbols2)
        if diff_len < 15:
          util.log(f, f"  {'':<32}  {sorted(list(symbols1-symbols2))}")
        else:
          util.log(f, f"  {'':<32}  {sorted(list(symbols1-symbols2))[0:15]}...")
          # util.log(f, f"  {'':<32}  Too many missing symbols: Skipping!!")
          #continue

        if len(symbols1 & symbols2) < (len(symbols1)*0.5):
          util.log(f, f"  {'':<32}  Too few shared symbols: Skipping!!")
          continue

        best_x = best_y = 0
        score = 0
        best_score = top_score
        if args.best_fit:
          (best_x, best_y, best_score) = fastSearchBestAlignment(font1, font2, step = 3)

          # if quicksearch gives an score < 0.1 then there is no match so we can skip
          if best_score > 0.1:
            (best_x, best_y, best_score) = fastSearchBestAlignment(
              font1,
              font2,
              step = 1,
              search_space = 3,
              x = best_x,
              y = best_y
            )

          util.log(f, f"  {'Best alignment':<32}: ({best_x}, {best_y}, score={best_score:.3f}) {'BEST!!' if best_score > top_score else ''}")
          if best_score > top_score:
            top_score = best_score

          score = best_score

        if best_score < 0.75*top_score:
          util.log(f, f"  {'Best score is poor':<32}: Skipping non-promising font!")

        elif args.exhaustive_search:
          (score, _) = compareFonts(
            font1,
            font2,
            xoffset = best_x,
            yoffset = best_y,
            file_prefix=diff_folder + "/" + prefix,
            alphabet = alphabet
          )

        end_time = time.time()
        util.log(f, f"  Took {end_time-start_time:.3f} seconds (total of {time.time() - script_start_time:.3f} seconds so far)")

        matches.append ({
          'font' : font2,
          'score' : score,
          'nmissing' : len(symbols1-symbols2),
          'nshared' : len(symbols1&symbols2),
          'nwanted' : len(symbols1),
          'best_x' : best_x,
          'best_y' : best_y
        })
      except Exception as e:
        util.log(f, f"  ERROR processing {font2}: {e}")
        continue

    # generate a list of best matches
    top_count = 50
    top_matches = sorted(matches, key=lambda x: x['score'], reverse=True)
    top_folder = diff_folder + '/top'
    gif_folder_fonts = top_folder + '-gif'
    diff_folder_fonts = top_folder + '-diff'
    top_folder_fonts = top_folder + '-fonts'

    os.makedirs(top_folder, exist_ok=True)
    os.makedirs(gif_folder_fonts, exist_ok=True)
    os.makedirs(diff_folder_fonts, exist_ok=True)
    os.makedirs(top_folder_fonts, exist_ok=True)

    shutil.copy2(font1, diff_folder)

    util.log(f, "\n\nTop matches by score (first pass):")
    best_fonts = []
    fonts_diff = {}
    for i, x in enumerate(top_matches[0:top_count]):
      util.log(f, f"  #{i+1:<2d} {x['font']:<32}: alignment  =({x['best_x']:2d}, {x['best_y']:2d}) score={x['score']:<1.3f} shared={x['nshared']} missing={x['nmissing']} wanted={x['nwanted']}")

      font2  = x['font']
      prefix = os.path.splitext(os.path.basename(font2))[0].lower()

      # recompute best alignment, since sometimes it might not be 100% ok
      # (best_x, best_y, best_score) = searchBestAlignment(font1, font2)
      best_x = x['best_x']
      best_y = x['best_y']
      best_score = x['score']
      (score, diff) = compareFonts(
        font1,
        font2,
        xoffset = best_x,
        yoffset = best_y,
        file_prefix=top_folder + "/" + prefix,
        alphabet=alphabet
      )
      best_fonts.append ({
        'font' : font2,
        'best_x' : best_x,
        'best_y': best_y,
        'nmissing': x['nmissing'],
        'nshared': x['nshared'],
        'nwanted': x['nwanted'],
        'score' : score,
      })
      fonts_diff[font2] = diff

      shutil.copy2(font2, top_folder_fonts)

    util.log(f, "\n")
    util.log(f, json.dumps(best_fonts, indent=2))

    util.log(f, "\n\nTop matches by score (final pass):")
    best_fonts = sorted(best_fonts, key=lambda x: x['score'], reverse=True)
    for i, x in enumerate(best_fonts):
      font2 = x['font']
      util.log(f, f"  #{i+1:<2d} {font2:<32}: alignment  =({x['best_x']:2d}, {x['best_y']:2d}) score={x['score']:<1.3f} shared={x['nshared']} missing={x['nmissing']} wanted={x['nwanted']}")

      # save diff to another folder, sorted by score
      (_, file) = os.path.split(font2)
      diff = fonts_diff[font2]
      diff.save(f"{diff_folder_fonts}/{i+1:03d}-{file}-s{x['score']:1.3f}.png")
      image1 = util.drawSymbolMatrix(
        STANDARD_ALPHABET,
        None,
        font1,
        title=os.path.basename(font1)
      )
      image2 = util.drawSymbolMatrix(
        STANDARD_ALPHABET,
        None,
        font2,
        title=f"{os.path.basename(font2)} offset={x['best_x']}, {x['best_y']}  score={x['score']}",
        xoffset = x['best_x'],
        yoffset = x['best_y']
      )
      image1.save(
        f"{gif_folder_fonts}/{i+1:03d}-{file}-s{x['score']:1.3f}.gif",
        append_images=[image2],
        save_all = True,
        duration = 750,
        loop = 0
      )


    best_fonts = [{'source_font' : font1, 'nsymbols' : len(symbols1)}] + best_fonts
    with open(f"{diff_folder}/analysis-top.json", "wt") as f2:
      util.log(f2, json.dumps(best_fonts, indent=2))

    util.log(f, f"\nScript Took: {time.time()-script_start_time:.3f} seconds")

if __name__ == '__main__':
  main()
