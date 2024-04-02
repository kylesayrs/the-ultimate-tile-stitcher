from typing import Tuple

import os
from PIL import Image
import argparse
import glob
import tqdm

def parse_args():
    parser = argparse.ArgumentParser(description='stitch tiles scraped by scraper.py')
    parser.add_argument('--dir', required=True, type=str, help='directory containing times, saved in {zoom}_{X}_{Y} form')
    parser.add_argument('--out-file', required=True, type=str, help='output filename')
    opts = parser.parse_args()
    return opts


def file_path_to_xyz(file_path: str) -> Tuple[int, int, int]:
        base = os.path.basename(file_path)
        z, x, y = base.split('_')
        y = os.path.splitext(y)[0]
        return int(x), int(y), int(z)


def main():
    opts = parse_args()
    search_path = os.path.join(opts.dir, '*_*_*.png')
    
    # read file paths
    file_paths = glob.glob(search_path)
    if len(file_paths) == 0:
        raise ValueError('No files found')

    # get tile extents
    xyzs = [
        file_path_to_xyz(file_path)
        for file_path in file_paths
    ]
    tile_extents = [
        (min(positions), max(positions) + 1)  # extent of the bottom right tile
        for positions in zip(*xyzs)
    ]

    # compute output size
    tile_width, tile_height = Image.open(file_paths[0]).size
    out_width = (tile_extents[0][1] - tile_extents[0][0]) * tile_width
    out_height = (tile_extents[1][1] - tile_extents[1][0]) * tile_height

    # create output image
    out_img = Image.new('RGBA', (out_width, out_height), (0, 0, 255, 0))
    for file_path, (x, y, z) in tqdm.tqdm(zip(file_paths, xyzs)):
        # compute offset
        x_pixel_offset = (x - tile_extents[0][0]) * tile_width
        y_pixel_offset = (y - tile_extents[1][0]) * tile_height

        # paste tile
        out_img.paste(
            Image.open(file_path),
            box=(
                x_pixel_offset,
                y_pixel_offset,
                x_pixel_offset + tile_width,
                y_pixel_offset + tile_height
            )
        )

    print(f'Saving stitch to {opts.out_file}')
    out_img.save(opts.out_file)


if __name__ == '__main__':
    main()
