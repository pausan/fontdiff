
#
# Filter fonts with the same charset as the one provided
#
import sys
import os
import time
import glob
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageSequence

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
  $ python3 charsetfilter.py -v FontName.ttf google-fonts
  $ python3 charsetfilter.py -d outdir -b -v path/to/Font.ttf folder/containing/fonts
    """
  )

  parser.add_argument('-d', '--out-dir', help="Output folder where images/diffs/etc will be generated")
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('input_font')
  parser.add_argument('font_search_path')


  CHARSET_TEXT_MAP = {
    "latin": "The quick brown fox jumps over the lazy dog.",
    "latin-ext": "ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÆŒÇÑßÅØÞÆŁĐØÞßæœçñåøþłđ",
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
    args.out_dir = f'tmp/charset-{out_dir}-{out_hash[0:8]}'.lower()
    os.makedirs(args.out_dir, exist_ok = True)
  out_dir = args.out_dir

  font1_path = args.input_font
  if os.path.isfile(args.font_search_path):
    font_files = [args.font_search_path]

  else:
    root_dir = args.font_search_path
    ttf_files = list(glob.glob('**/*.ttf', root_dir = root_dir, recursive = True))
    otf_files = list(glob.glob('**/*.otf', root_dir = root_dir, recursive = True))
    font_files = list(sorted(ttf_files + otf_files))
    font_files = [os.path.join(root_dir, file) for file in font_files]

  arial_font = ImageFont.truetype("Arial", 12)
  script_start_time = time.time()
  with open(f"{args.out_dir}/analysis.txt", "wt") as f:
    symbols1 = util.getSymbolIds(font1_path)

    font1charsets = set()
    for charset, text in CHARSET_TEXT_MAP.items():
      # only draw charsets available on the first font
      if len(set([ord(x) for x in text]) & symbols1) > 3:
        font1charsets.add(charset)

    print("- Charsets found: ", ', '.join(sorted(list(font1charsets))))

    util.log(f, f"Comparing with font: {font1_path:<32}")
    util.log(f, f"{font1_path:<32}: {len(symbols1)} glyphs")

    # NOTE: adding font1 as a reference
    font_files = [font1_path] + font_files

    MAX_HEIGHT = 900
    font_size = 32
    padding   = 32
    image_height = min(2*padding + len(font_files) * (font_size+padding), MAX_HEIGHT)
    image1 = Image.new("RGB", (1440, image_height), "white")
    image2 = Image.new("RGB", (1440, image_height), "white")
    draw1 = ImageDraw.Draw(image1)
    draw2 = ImageDraw.Draw(image2)

    font1 = ImageFont.truetype(font1_path, font_size)

    image_y = padding
    for idx, ttf_file in enumerate(font_files):
      if font1_path == ttf_file:
        continue

      symbols2 = util.getSymbolIds(ttf_file)

      font2charsets = set()
      for charset, text in CHARSET_TEXT_MAP.items():
        # only draw charsets available on the first font
        if len(set([ord(x) for x in text]) & symbols2) > 3:
          font2charsets.add(charset)

      if len(font1charsets.intersection(font2charsets)) < len(font1charsets) - 2:
        util.log (f, "Missing charsets. Skipping")
        continue

      font2_path = ttf_file
      font2 = ImageFont.truetype(font2_path, font_size)

      #image1 = Image.new("RGB", (1024, image_height), "white")
      image2 = Image.new("RGB", (1024, image_height), "white")
      #draw1 = ImageDraw.Draw(image1)
      draw2 = ImageDraw.Draw(image2)

      image_y = padding
      for charset, text in CHARSET_TEXT_MAP.items():
        if charset not in font1charsets:
          continue

        util.log(f, f"Drawing {charset:<12} {os.path.basename(font2_path)}")
        # draw1.text((padding, image_y-14), f"{charset.upper()} - {os.path.basename(font1_path)}", font=arial_font, fill="#f60")
        # draw1.text((padding, image_y), text, font=font1, fill="black")

        draw2.text((padding, image_y-14), f"{charset.upper()} - {os.path.basename(font2_path)}", font=arial_font, fill="#f60")
        draw2.text((padding, image_y), text, font=font2, fill="black")
        image_y += padding + font_size

      #image1.save(f"{args.out_dir}/charset-{os.path.basename(font2_path).lower()}_0.png")
      image2.save(f"{args.out_dir}/charset-{os.path.basename(font2_path).lower()}.png")

    util.log(f, f"\nScript Took: {time.time()-script_start_time:.3f} seconds")

if __name__ == '__main__':
  main()
