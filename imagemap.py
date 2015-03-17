import re
import operator
import itertools
import collections


InputImageBase = collections.namedtuple(
    'InputImage', 'filename width height'.split())


class InputImage(InputImageBase):
    dimensions = property(lambda self: (self.width, self.height))
    area = property(lambda self: self.width * self.height)


Position = collections.namedtuple('Position', 'left top'.split())


class PackedImage(object):
    def __init__(self, im, pos):
        self._im = im
        self._pos = pos

    def __getattr__(self, attr):
        try:
            return getattr(self._im, attr)
        except AttributeError:
            return getattr(self._pos, attr)

    right = property(lambda self: self.left + self.width)
    bottom = property(lambda self: self.top + self.height)


def histogram(xs, attr):
    key = operator.attrgetter(attr)
    xs = sorted(xs, key=key)
    return [(k, list(vs)) for k, vs in itertools.groupby(xs, key=key)]


class Packing(object):
    def __init__(self, images):
        self.images = images
        self.input_area = sum(im.area for im in images)
        self.top = min(im.top for im in images)
        self.left = min(im.left for im in images)
        self.bottom = max(im.bottom for im in images)
        self.right = max(im.right for im in images)
        self.width = self.right - self.left
        self.height = self.bottom - self.top
        self.area = self.width * self.height


def naive_packing(by_height):
    def bins_for_width(width):
        bins = []
        for height, ims in by_height:
            row = None
            rows = []
            row_width = width
            for im in ims:
                if row_width + im.width > width:
                    row = []
                    rows.append(row)
                    row_width = 0
                row.append(im)
                row_width += im.width
            bins.append((height, rows))
        return bins

    def packing_for_width(width):
        bins = bins_for_width(width)
        packing = []
        y = 0
        for height, rows in bins:
            for row in rows:
                x = 0
                max_height = 0
                for im in row:
                    packing.append(PackedImage(im, Position(x, y)))
                    max_height = max(max_height, im.height)
                    x += im.width
                y += max_height
        return Packing(packing)

    min_width = max(im.width for h, ims in by_height for im in ims)
    max_width = max(sum(im.width for im in ims) for h, ims in by_height)

    width = max_width
    packings = []
    while width >= min_width:
        p = packing_for_width(width)
        # print("Computed packing for width %s" % p.width)
        width = p.width - 1
        packings.append(p)
    best = min(packings, key=operator.attrgetter('area'))
    print("naive_packing: Best is width %s at area %s" %
          (best.width, best.area))
    return best


def write_packing(packing, filename):
    with open(filename, 'w') as fp:
        for image in packing.images:
            fp.write(
                ('<img src="{im.filename}" ' +
                 'style="position:absolute;' +
                 'left:{im.left}px;top:{im.top}px"/>\n').format(im=image))


def small_height_reduction(by_height):
    packings = []
    for i in range(len(by_height)):
        collapsed = []
        for j in range(i + 1):
            collapsed += by_height[j][1]
        collapsed_by_height = [(by_height[i][0], collapsed)] + by_height[i + 1:]
        packing = naive_packing(collapsed_by_height)
        print("Collapse all smaller than %s => %s" % (by_height[i][0], packing.area))
        packings.append(packing)
    best = min(packings, key=operator.attrgetter('area'))
    print("small_height_reduction: Best is area %s" % (best.area,))
    return best


def and_the_transpose(f, images):
    p1 = f(histogram(images, 'height'))
    im_transpose = []
    for im in images:
        im_transpose.append(
            InputImage(filename=im.filename, width=im.height, height=im.width))
    p2 = f(histogram(im_transpose, 'height'))
    if p1.area < p2.area:
        return p1
    packing_transpose = []
    for pim in p2.images:
        im = InputImage(
            filename=pim.filename, width=pim.height, height=pim.width)
        pos = Position(top=pim.left, left=pim.top)
        packing_transpose.append(PackedImage(im, pos))
    return Packing(packing_transpose)


def main():
    images = []
    with open('input.txt') as fp:
        for line in fp:
            if line.startswith('#'):
                continue
            o = re.search(r'(.*):.*, (\d+) x (\d+)', line)
            if not o:
                raise ValueError(repr(line))
            im = InputImage(o.group(1), 1 + int(o.group(2)), 1 + int(o.group(3)))
            images.append(im)
    total_size = sum(im.area for im in images)
    target = total_size / (1 - 0.28546)
    # target = 414 * 374
    print("%d images" % len(images))
    by_size = histogram(images, 'dimensions')
    by_width = histogram(images, 'width')
    by_height = histogram(images, 'height')
    print("%d different sizes" % len(by_size))
    print("%d different widths" % len(by_width))
    print("%d different heights" % len(by_height))
    print("Total size is %d, and we want to do better than %d pixels" %
          (total_size, target))
    print("imagemap.png is %d, so the input is sum %d" %
          (414 * 374, 414 * 374 * (1 - 0.28546)))

    by_area = sorted(by_size, key=lambda x: x[1][0].area)
    for sz, ims in by_area:
        print("%d images of size %s area %d" % (len(ims), sz, ims[0].area))

    packing = and_the_transpose(small_height_reduction, images)

    write_packing(packing, 'images/imagemap.html')


if __name__ == "__main__":
    main()
