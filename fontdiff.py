
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
import math
import sys
import os
import time
import glob
import json
import argparse
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageChops
from fontTools import ttLib
import numpy


#  for glyph_codepoint, glyph_name in cmap.items():
#    print(f"Glyph: {glyph_id}, {gid} Unicode Codepoint: {name}")

  # font1 = ttLib.TTFont(font_path1)
  # font2 = ttLib.TTFont(font_path2)

  # cmap = font1.getBestCmap() # Cmap = character map
  # for glyph, char_code in cmap.items():
  #   print(f"Glyph: {glyph}, Character: {char_code}")

  # symbols1 = font1.getGlyphSet().keys()
  # symbols2 = font2.getGlyphSet().keys()

  # print (f"Font1 has {len(symbols1)} glyphs")
  # print (f"Font2 has {len(symbols2)} glyphs")

  # symbols1_lookup = {}
  # for glyph_name in symbols1:
  #   gid = font1.getGlyphID(glyph_name)
  #   symbols1_lookup[gid] = glyph_name

  # symbols2_lookup = {}
  # for glyph_name in symbols2:
  #   gid = font2.getGlyphID(glyph_name)
  #   symbols2_lookup[gid] = glyph_name

g_font_size = 32
g_padding = 4

def drawText(text, font_path, out_file = None):
  font = ImageFont.truetype(font_path, g_font_size)

  (_left, _top, text_width, text_height) = font.getbbox(text)

  image_width = 2*g_padding + text_width
  image_height = 2*g_padding + text_height

  image = Image.new("RGB", (image_width, image_height), "white")
  draw = ImageDraw.Draw(image)

  draw.text((g_padding, g_padding), text, font=font, fill="black")

  if out_file:
    image.save(out_file)

  return image

def drawSymbolMatrix(symbols, size, font_path, title = None, xoffset = 0, yoffset = 0):
  """ yoffset helps skew font drawing
  """
  title_padding = 64 if title else 0

  image_width = 2*g_padding + g_font_size*size
  image_height = title_padding + g_padding + (g_padding + g_font_size)*size
  # (_left, _top, text_width, text_height) = font.getbbox(line)

  font = ImageFont.truetype(font_path, g_font_size)
  image = Image.new("RGB", (image_width, image_height), "white")
  draw = ImageDraw.Draw(image)

  if title:
    title_font = ImageFont.truetype("Arial.ttf", 16)
    draw.text((8, 8), title, font=title_font, fill="black")

  for i, symbol in enumerate(symbols):
    x = xoffset + g_padding + (i%size)*g_font_size
    y = yoffset + title_padding + g_padding + ((i-i%size)/size)*g_font_size

    draw.text((x,y), symbol, font=font, fill="black")

  return image


def getSymbolIds(font_path):
  font = ttLib.TTFont(font_path)
  cmap = font.getBestCmap()
  return set(cmap.keys())

def compareFonts(
  font_path1,
  font_path2,
  xoffset = 0,
  yoffset = 0,
  file_prefix = "",
  max_items_to_compare = None
):
  symbols1 = getSymbolIds(font_path1)
  symbols2 = getSymbolIds(font_path2)
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
  if max_items_to_compare:
    codepoints_shared=codepoints_shared[0:max_items_to_compare]

  shared_size = math.ceil(len(codepoints_shared)**0.5)

  (sim_score, diff) = getFontDiffScore(
    codepoints_shared,
    shared_size,
    font_path1,
    font_path2,
    xoffset = xoffset,
    yoffset = yoffset
  )

  # if diff.getbbox() is not None:
  image1 = drawSymbolMatrix(
    codepoints,
    size,
    font_path1,
    title=font_path1
  )
  image2 = drawSymbolMatrix(
    codepoints,
    size,
    font_path2,
    title=f"{font_path2} with offset {xoffset}, {yoffset}",
    xoffset = xoffset,
    yoffset = yoffset
  )
  image_missing = drawSymbolMatrix(
    codepoints_missing_from2,
    size,
    font_path1,
    title=f"{len(symbols1 - symbols2)} {font_path1} chars not in {font_path2}"
  )

  image1.save(f"{file_prefix}_font1.png")
  image2.save(f"{file_prefix}_font2.png")
  image_missing.save(f"{file_prefix}3_missing.png")
  diff.save(f"{file_prefix}_diff.png")

  # save diff to another folder
  (folder, file) = os.path.split(file_prefix)
  os.makedirs(f'{folder}/diff', exist_ok = True)
  shutil.copy2(f"{file_prefix}_diff.png", f"{folder}/diff/{file}.png")

  return (sim_score)

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
  im1 = drawSymbolMatrix(codepoints_shared, size, font_path1)
  im2 = drawSymbolMatrix(codepoints_shared, size, font_path2, xoffset = xoffset, yoffset = yoffset)

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
        'A3K#', # 4 random letters
        2,      # 2x2 grid
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

  symbols1 = getSymbolIds(font_path1)
  symbols2 = getSymbolIds(font_path2)

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

def log(f, message):
  print(message)
  if f:
    f.write(message)
    f.write("\n")
    f.flush()
  return

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

  parser.add_argument('--fast-search', action='store_true', help="Fast exploration to skip expensive comparisons (implies -b)")
  parser.add_argument('-b', '--best-fit', action='store_true', help="On each font, try to find the best fit")
  parser.add_argument('-d', '--out-dir', default="fdiff", help="Output folder where images/diffs/etc will be generated")
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('input_font')
  parser.add_argument('font_search_path')

  args = parser.parse_args()
  verbose = args.verbose

  # if we want fast search we should go for best_fit for sure
  if args.fast_search:
    args.best_fit = True
  args.exhaustive_search = not args.fast_search

  diff_folder = args.out_dir
  os.makedirs(diff_folder, exist_ok=True)

  font1 = args.input_font
  if os.path.isfile(args.font_search_path):
    ttf_files = [args.font_search_path]

  else:
    root_dir = args.font_search_path
    ttf_files = list(glob.glob('**/*.ttf', root_dir = root_dir, recursive = True))
    ttf_files = [os.path.join(root_dir, file) for file in ttf_files]

  # extract copyright/license/...
  # font = ttLib.TTFont(font2)
  # for record in font["name"].names:
  #   print(record)

  script_start_time = time.time()
  with open(f"{diff_folder}/analysis.txt", "at") as f:
    symbols1 = getSymbolIds(font1)

    log(f, f"Finding best match for: {font1:<32}")
    log(f, f"{font1:<32}: {len(symbols1)} glyphs")
    matches = []

    top_score = 0
    for idx, ttf_file in enumerate(ttf_files):
      font2 = ttf_file
      try:

        start_time = time.time()
        log(f, f"\n[{idx+1}/{len(ttf_files)}] {font2}")

        prefix = os.path.splitext(os.path.basename(font2))[0].lower()
        symbols2 = getSymbolIds(font2)
        log(f, f"  {'Total glyps':<32}: {len(symbols1 | symbols2)} glyphs on both fonts")
        log(f, f"  {os.path.basename(font2):<32}: {len(symbols2)} glyphs (vs {len(symbols1)})")
        log(f, f"  {os.path.basename(font2):<32}: {len(symbols1&symbols2)} glyphs shared with {font1} (vs {len(symbols1)})")
        log(f, f"  {os.path.basename(font2):<32}: {len(symbols1-symbols2)} glyphs missing from {font1}")

        diff_len = len(symbols1-symbols2)
        if diff_len < 15:
          log(f, f"  {'':<32}  {sorted(list(symbols1-symbols2))}")
        else:
          log(f, f"  {'':<32}  {sorted(list(symbols1-symbols2))[0:15]}...")
          # log(f, f"  {'':<32}  Too many missing symbols: Skipping!!")
          #continue

        if len(symbols1 & symbols2) < (len(symbols1)*0.95):
          log(f, f"  {'':<32}  Too few shared symbols: Skipping!!")
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

          log(f, f"  {'Best alignment':<32}: ({best_x}, {best_y}, score={best_score:.3f}) {'BEST!!' if best_score > top_score else ''}")
          if best_score > top_score:
            top_score = best_score

          score = best_score

        if best_score < 0.75*top_score:
          log(f, f"  {'Best score is poor':<32}: Skipping non-promising font!")

        elif args.exhaustive_search:
          score = compareFonts(
            font1,
            font2,
            xoffset = best_x,
            yoffset = best_y,
            file_prefix=diff_folder + "/" + prefix,
            max_items_to_compare = 25 # TODO
          )

        end_time = time.time()
        log(f, f"  Took {end_time-start_time:.3f} seconds (total of {time.time() - script_start_time:.3f} seconds so far)")

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
        log(f, f"  ERROR processing {font2}: {e}")
        continue

    # generate a list of best matches
    top_matches = sorted(matches, key=lambda x: x['score'], reverse=True)
    top25_folder = diff_folder + 'top25'
    os.makedirs(top25_folder, exist_ok=True)
    top25_folder_fonts = diff_folder + 'top25/fonts'
    os.makedirs(top25_folder_fonts, exist_ok=True)

    log(f, "\n\nTop 25 matches by score:")
    best_fonts = []
    for i, x in enumerate(top_matches[0:25]):
      log(f, f"  #{i+1:<2d} {x['font']:<32}: alignment  =({x['best_x']:2d}, {x['best_y']:2d}) score={x['score']:<1.3f} shared={x['nshared']} missing={x['nmissing']} wanted={x['nwanted']}")

      font2  = x['font']
      prefix = os.path.splitext(os.path.basename(font2))[0].lower()

      # recompute best alignment, since sometimes it might not be 100% ok
      (best_x, best_y, best_score) = searchBestAlignment(font1, font2)
      score = compareFonts(
        font1,
        font2,
        xoffset = best_x,
        yoffset = best_y,
        file_prefix=top25_folder + "/" + prefix
      )
      best_fonts.append ({
        'font' : font2,
        'best_x' : best_x,
        'best_y': best_y,
        'nmissing': x['nmissing'],
        'nshared': x['nshared'],
        'nwanted': x['nwanted'],
        'score' : score
      })

      shutil.copy2(font2, top25_folder_fonts)

    log(f, "\n")
    log(f, json.dumps(best_fonts, indent=2))

    best_fonts = sorted(best_fonts, key=lambda x: x['score'], reverse=True)
    for i, x in enumerate(best_fonts):
      log(f, f"  #{i+1:<2d} {x['font']:<32}: alignment  =({x['best_x']:2d}, {x['best_y']:2d}) score={x['score']:<1.3f} shared={x['nshared']} missing={x['nmissing']} wanted={x['nwanted']}")

    best_fonts = [{'source_font' : font1, 'nsymbols' : len(symbols1)}] + best_fonts
    with open(f"{diff_folder}/analysis-top25.json", "wt") as f2:
      log(f2, json.dumps(best_fonts, indent=2))

    log(f, f"\nScript Took: {time.time()-script_start_time:.3f} seconds")

if __name__ == '__main__':
  main()
