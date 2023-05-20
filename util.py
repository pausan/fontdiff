
import math
import os
import time
import hashlib
import _pickle as pickle
from PIL import Image, ImageDraw, ImageFont
from fontTools import ttLib
import util

CACHE_DIR = './.cache'
CACHE_FORMAT = '.png'
g_font_size = 32
g_padding = 4
g_symbolIdsCache = {}
g_imageCache = {}
g_imageCacheLastPurge = time.time()

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



def init():
  """ Make sure some cache folders exist, ...
  """
  os.makedirs(f'{CACHE_DIR}/symbols', exist_ok=True)
  for i in range(0, 256):
    os.makedirs(f'{CACHE_DIR}/{i:02x}', exist_ok=True)


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

class CachedImage:
  def __init__(self, image):
    self.image = image
    self.hits = 0
    self.last_updated = time.time()

  def hit(self):
    self.hits += 1
    self.last_updated = time.time()

  def isExpired(self):
    """ Let's expire everything that has not had more than 5 hits and is older
    than one minute
    """
    # if self.hits < 5:
    if (time.time() - self.last_updated) > 60:
      return True
    return False

def drawSymbolMatrix(symbols, size, font_path, title = None, xoffset = 0, yoffset = 0):
  """ yoffset helps skew font drawing
  """
  global g_imageCache, g_imageCacheLastPurge
  if not size:
    size = math.ceil(len(symbols)**0.5)

  if size > 32:
    #print (f"WARN: Huge size! Trimming down from size={size}, nsymbols={len(symbols)} to size=32, nsymbols=1024")
    symbols = symbols[:1024]
    size    = 32

  title_padding = 64 if title else 0

  image_width = 2*g_padding + g_font_size*size
  image_height = title_padding + g_padding + (g_padding + g_font_size)*size

  # (_left, _top, text_width, text_height) = font.getbbox(line)

  # Since this method is called with same params and different offsets
  # we can make it go faster by not rendering text again, so faster than drawing
  # symbol matrix is to check if we just drawn the same thing with offset=0,0
  # and then just recover the image and create another image drawing with
  # desired offset so we only cache stuff with offset 0, 0
  if xoffset != 0 and yoffset != 0:
    cachedImage = drawSymbolMatrix(symbols, size, font_path, title, xoffset = 0, yoffset = 0)
    image = Image.new("RGB", (image_width, image_height), "white")
    image.paste(cachedImage, (xoffset, yoffset))
    return image

  h = hashlib.blake2s()
  h.update(f"{symbols}-{size}-{font_path}-{title}-{xoffset}-{yoffset}".encode())
  cacheId = h.hexdigest()
  cached = g_imageCache.get(cacheId, None)
  if cached:
    cached.hit()
    return cached.image

  diskCacheId = f'{CACHE_DIR}/{cacheId[0:2]}/{cacheId[2:]}.{CACHE_FORMAT}'
  if os.path.isfile(diskCacheId):
    return Image.open(diskCacheId)

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

  g_imageCache[cacheId] = CachedImage(image)

  # purge every X seconds, to free memory
  if (len(g_imageCache) > 100 and (time.time() - g_imageCacheLastPurge) > 30):
    g_imageCache = {k:v for k, v in g_imageCache.items() if not v.isExpired() }
    g_imageCacheLastPurge = time.time()

  image.save(diskCacheId)
  return image

def fontSymbolIsEmpty(font, glyph_name):
  """ Returns True if given symbol/glyph is empty
  """
  glyph = font['glyf'][glyph_name]

  has_contours = glyph.numberOfContours != -1
  has_components = glyph.components is not None

  return not (has_contours or has_components)


def log(f, message):
  print(message)
  if f:
    f.write(message)
    f.write("\n")
    f.flush()
  return


def getFileMd5(file_path):
  """ Generate the MD5 hash since it is later simpler to use it on the commandline
  """
  md5hash = hashlib.md5()
  with open(file_path, 'rb') as file:
    for chunk in iter(lambda: file.read(4096), b''):
      md5hash.update(chunk)
  return md5hash.hexdigest()

def getSymbolIds(font_path):
  """ Return non-empty symbol IDs. Please note that simple/composite glyphs
  that contain no rendering will be skipped, since in the end, defining
  a symbol only to be left empty, is like if it was not defined in the first
  place.
  """
  global g_symbolIdsCache
  if font_path in g_symbolIdsCache:
    return g_symbolIdsCache[font_path]

  font_path
  h = hashlib.blake2s()
  h.update(f"font-{font_path}".encode())
  cacheId = h.hexdigest()
  diskCacheId = f'{CACHE_DIR}/symbols/{cacheId[2:]}.symbols'
  if os.path.isfile(diskCacheId):
    with open(diskCacheId, 'rb') as f:
      return pickle.load(f)

  font = ttLib.TTFont(font_path)
  cmap = font.getBestCmap()

  # Note: we can return all symbols by doing this: return set(cmap.keys())

  glyph_set = font.getGlyphSet()

  # we want to get all symbol ids that are not empty/blank, we want glyphs
  # that draw something on the screen
  symbols = set()
  for char, name in cmap.items():
    try:
      glyph = font['glyf'][name]

      if glyph.isComposite():
        is_empty_glyph = glyph.components is None
      else:
        is_empty_glyph = glyph.numberOfContours <= 0

      if is_empty_glyph:
        continue
    except:
      pass

    symbols.add(char)

  g_symbolIdsCache = symbols

  with open(diskCacheId, 'wb') as f:
    pickle.dump(symbols, f)

  return symbols
