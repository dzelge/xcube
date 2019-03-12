from typing import Any, Dict

import click

from xcube.cli.gen import gen
from xcube.cli.grid import grid
from xcube.version import version


def _parse_kwargs(value: str, metavar: str = None) -> Dict[str, Any]:
    if value:
        try:
            return eval(f"dict({value})", {}, {})
        except Exception:
            if metavar:
                message = f"Invalid value for {metavar}: {value!r}"
            else:
                message = f"Invalid value: {value!r}"
            raise click.ClickException(message)
    else:
        return dict()


# noinspection PyShadowingBuiltins
@click.command(name="extract")
@click.argument('cube', metavar='<cube>')
@click.argument('coords', metavar='<coords>')
@click.option('--indexes', '-i', is_flag=True,
              help="Include indexes in output.")
@click.option('--output', '-o', metavar='<output>',
              help="Output file.")
@click.option('--format', '-f', metavar='<format>', type=click.Choice(['csv', 'stdout']),
              help="Format of the output. If not given, guessed from <output>, otherwise <stdout> is used.")
@click.option('--params', '-p', metavar='<params>',
              help="Parameters specific for the output format."
                   " Comma-separated list of <key>=<value> pairs.")
def extract(cube, coords, indexes=False, output=None, format=None, params=None):
    """
    Extract data from <cube> at points given by coordinates <coords>.
    """
    import pandas as pd

    cube_path = cube
    coords_path = coords
    output_path = output
    include_indexes = indexes

    from xcube.api import open_dataset, get_cube_values_for_points

    coords = pd.read_csv(coords_path, parse_dates=["time"], infer_datetime_format=True)
    print(coords, [coords[c].values.dtype for c in coords])
    with open_dataset(cube_path) as cube:
        values = get_cube_values_for_points(cube, coords, include_indexes=include_indexes)
        if output_path:
            values.to_csv(output_path)
        else:
            print(values)


# noinspection PyShadowingBuiltins
@click.command(name="chunk")
@click.argument('input', metavar='<input>')
@click.argument('output', metavar='<output>')
@click.option('--format', '-f', metavar='<format>', type=click.Choice(['zarr', 'netcdf']),
              help="Format of the output. If not given, guessed from <output>.")
@click.option('--params', '-p', metavar='<params>',
              help="Parameters specific for the output format."
                   " Comma-separated list of <key>=<value> pairs.")
@click.option('--chunks', '-c', metavar='<chunks>', nargs=1, default=None,
              help='Chunk sizes for each dimension.'
                   ' Comma-separated list of <dim>=<size> pairs,'
                   ' e.g. "time=1,lat=270,lon=270"')
def chunk(input, output, format=None, params=None, chunks=None):
    """
    Write a new dataset with identical data and compression but with new chunk sizes.
    """
    chunk_sizes = None
    if chunks:
        chunk_sizes = _parse_kwargs(chunks, metavar="<chunks>")
        for k, v in chunk_sizes.items():
            if not isinstance(v, int) or v <= 0:
                raise click.ClickException("Invalid value for <chunks>, "
                                           f"chunk sizes must be positive integers: {chunks}")

    write_kwargs = dict()
    if params:
        write_kwargs = _parse_kwargs(params, metavar="<params>")

    from xcube.util.dsio import guess_dataset_format
    format_name = format if format else guess_dataset_format(output)

    from xcube.api import open_dataset, chunk_dataset, write_dataset

    with open_dataset(input_path=input) as ds:
        if chunk_sizes:
            for k in chunk_sizes:
                if k not in ds.dims:
                    raise click.ClickException("Invalid value for <chunks>, "
                                               f"{k!r} is not the name of any dimension: {chunks}")

        chunked_dataset = chunk_dataset(ds, chunk_sizes=chunk_sizes, format_name=format_name)
        write_dataset(chunked_dataset, output_path=output, format_name=format_name, **write_kwargs)


@click.command(name="pyram")
@click.argument('input', metavar='<input>')
@click.option('--output', '-o', metavar='<output>',
              help='Output directory. If omitted, "<input>.levels" will be used.')
@click.option('--link', '-l', is_flag=True, flag_value=True,
              help='Link the <input> instead of converting it to a level zero dataset.')
def pyram(input, output, link):
    """
    Convert a dataset stored in <input> to its representation as a spatial image pyramid in directory <output>.
    """
    import time
    import os.path
    from xcube.api.pyramid import write_pyramid_levels

    input_path = input
    output_path = output
    link_input = link

    start_time = t0 = time.perf_counter()

    # noinspection PyUnusedLocal
    def progress_monitor(dataset, index, num_levels):
        nonlocal t0
        print(f"level {index} of {num_levels} written after {time.perf_counter() - t0} seconds")
        t0 = time.perf_counter()

    if not output_path:
        basename, ext = os.path.splitext(input_path)
        output_path = os.path.join(os.path.dirname(input_path), basename + ".levels")

    if os.path.exists(output_path):
        raise click.ClickException(f"output {output_path!r} already exists")

    levels = write_pyramid_levels(output_path,
                                  input_path=input_path,
                                  link_input=link_input,
                                  progress_monitor=progress_monitor)
    print(f"{len(levels)} levels written into {output_path} after {time.perf_counter() - start_time} seconds")


@click.command(name="dump")
@click.argument('dataset', metavar='<path>')
@click.option('--variable', '-v', metavar='<variable>', multiple=True,
              help="Name of a variable (multiple allowed).")
@click.option('--encoding', '-e', is_flag=True, flag_value=True,
              help="Dump also variable encoding information.")
def dump(dataset, variable, encoding):
    """
    Dump contents of dataset.
    """
    from xcube.api import open_dataset, dump_dataset
    with open_dataset(dataset) as ds:
        text = dump_dataset(ds, variable_names=variable, show_var_encoding=encoding)
        print(text)


# noinspection PyShadowingBuiltins
@click.group()
@click.version_option(version)
def cli():
    """
    Xcube Toolkit
    """


cli.add_command(chunk)
cli.add_command(dump)
cli.add_command(extract)
cli.add_command(grid)
cli.add_command(gen)
cli.add_command(pyram)


def main(args=None):
    cli.main(args=args)


if __name__ == '__main__':
    main()
