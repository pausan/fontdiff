
#
# Draw the same line of text using multiple fonts
#

import math
import sys
import os
import time
import glob
import json
import argparse
import hashlib
import shutil
import _pickle as pickle
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageSequence
from fontTools import ttLib
import numpy

import util

def main():
  parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    formatter_class=argparse.RawTextHelpFormatter,
    description="""
Analyze font and try to find a similar one
    """,
    epilog="""
Examples:
  $ python3 fontdiff.py -t "The Abc Of Text" -v FontName.ttf google-fonts
  $ python3 fontdiff.py --fast-search -d cmpdir -b -v path/to/Font.ttf folder/containing/fonts
    """
  )

  parser.add_argument('-d', '--out-dir', help="Output folder where images/diffs/etc will be generated")
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('input_font')

  CHARSET_TEXT_MAP = {
    "latin": "The quick brown fox jumps over the lazy dog.",
    "latinext": "ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÆŒÇÑßÅØÞÆŁĐØÞßæœçñåøþłđ",
    "cyrillic": "Быстрая коричневая лиса прыгает через ленивую собаку.",
    "greek": "Γρήγορη καφέ αλεπού πηδάει πάνω από το τεμπέλικο σκυλί.",
    "hebrew": "השועל החום המהיר קופץ מעל לטפשה העצלה.",
    "arabic": "الثعلب البني السريع يقفز فوق الكلب الكسول.",
    "devanagari": "तेज भूरी लोमड़ी आलसी कुत्ते पर कूदती है।",
    "chinese": "快速的棕色狐狸跳過过懒懶狗。",
    "japanese": "速い茶色のキツネは、怠け者の犬を飛び越えます。",
    "korean": "빠른 갈색 여우가 게으른 개를 뛰어넘습니다.",
    "thai": "หมาจิ้งจอกสีน้ำตาลเร็วกระโดดข้ามหมาเกียจคร้าน",
  }

  args = parser.parse_args()
  verbose = args.verbose

  if not args.out_dir:
    out_hash = util.getFileMd5(args.input_font)
    out_dir = os.path.split(os.path.splitext(args.input_font)[0])[1]
    args.out_dir = f'tmp-info-{out_dir}-{out_hash[0:8]}'.lower()
    os.makedirs(args.out_dir, exist_ok = True)
  out_dir = args.out_dir

  font1_path = args.input_font

  arial_font = ImageFont.truetype("Arial", 12)
  script_start_time = time.time()
  with open(f"{args.out_dir}/analysis.txt", "wt") as f:
    MAX_HEIGHT = 900
    font_size = 32
    padding   = 32
    image_height = min(2*padding + len(CHARSET_TEXT_MAP) * (font_size+padding), MAX_HEIGHT)

    if font1_path.endswith('.ttc'):
      util.log(f, "Multiple files found")
      util.log(f, f"MD5 of {font1_path}: {util.getFileMd5(font1_path)[:8]} {util.getFileMd5(font1_path)}")
      ttc_font = ttLib.TTCollection(font1_path)
      input_fonts = []
      for font_index, font in enumerate(ttc_font.fonts):
        new_font_path = os.path.join(f"{args.out_dir}/{os.path.basename(font1_path)}-{font_index}.ttf")
        font.save(new_font_path)
        input_fonts.append(new_font_path)
    else:
      input_fonts = [font1_path]

    for font1_path in input_fonts:
      util.log(f, f"MD5 of {font1_path}: {util.getFileMd5(font1_path)[:8]} {util.getFileMd5(font1_path)}")
      symbols1 = util.getSymbolIds(font1_path)
      font1 = ImageFont.truetype(font1_path, font_size)
      image1 = Image.new("RGB", (1440, image_height), "white")
      draw1 = ImageDraw.Draw(image1)

      image_y = padding
      font1charsets = []
      for charset, text in CHARSET_TEXT_MAP.items():
        if len(set([ord(x) for x in text]) & symbols1) < 3:
          continue

        font1charsets.append(charset)

        util.log(f, f"Drawing {charset:<12} {os.path.basename(font1_path)}")
        draw1.fontmode = "L" # antialias
        draw1.text((padding, image_y-14), f"{charset.upper()} - {os.path.basename(font1_path)}", font=arial_font, fill="#f60")
        draw1.text((padding, image_y), text, font=font1, fill="black")
        image_y += padding + font_size

      print("- Charsets found: ", ', '.join(font1charsets))

      image1.save(f"{args.out_dir}/{os.path.basename(font1_path).lower()}.png")

    util.log(f, f"\nScript Took: {time.time()-script_start_time:.3f} seconds")

if __name__ == '__main__':
  main()
