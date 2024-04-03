from typing import Tuple

import os
import tqdm
import glob
import numpy
import argparse
from PIL import Image
from osgeo import gdal, osr

from utils import tile2latlon

gdal.UseExceptions()


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
    # arguments and  validation
    opts = parse_args()
    if os.path.splitext(opts.out_file)[1].lower() != ".tif":
        raise ValueError("output file must end with .tif")
    
    # read file paths
    search_path = os.path.join(opts.dir, '*_*_*.png')
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

    # create geotiff
    out_image_array = numpy.array(out_img)

    # Create a new GeoTIFF file
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(opts.out_file, out_img.width, out_img.height, 3, gdal.GDT_Byte)

    # Write the array data into the GeoTIFF dataset
    for band_index in range(1, 4):
        dataset.GetRasterBand(band_index).WriteArray(out_image_array[:, :, band_index - 1])

    # Set geotransform
    tile_zoom = xyzs[0][2]
    min_lat, min_lon = tile2latlon(tile_extents[0][0], tile_extents[1][0], tile_zoom)
    max_lat, max_lon = tile2latlon(tile_extents[0][1], tile_extents[1][1], tile_zoom)
    pixel_size = (
        (max_lon - min_lon) / out_img.width,
        (max_lat - min_lat) / out_img.height
    )
    geotransform = (min_lon, pixel_size[0], 0.0, min_lat, 0.0, pixel_size[1])
    dataset.SetGeoTransform(geotransform)

    # Set projection
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    print(f'Saving stitch to {opts.out_file}')


if __name__ == '__main__':
    main()
