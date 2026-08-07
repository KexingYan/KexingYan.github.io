# Photography assets

Photography uses one safe seed dataset to produce public manifests for local and
production delivery. The authoritative seed is `data/photography/photos.seed.json`;
`data/photos.json` is generated public output and is not the long-term datastore.

## Asset modes

- Local mode serves ignored development derivatives from `generated/`.
- Production mode emits the same records with HTTPS URLs under the configured R2
  asset base. A production release contains no generated JPEG directory.

Every derivative name uses stable identity and an explicit asset version, for
example `P014-v1-display.jpg`. Replacing an image increments `assetVersion`; it
never overwrites an immutable URL.

The four derivative classes are 480px thumbnail, 1280px preview, 2200px display,
and 1800px personal-use download. JPEGs preserve an embedded sRGB profile when
available. Original EXIF is not copied. A minimal replacement EXIF block records
creator, copyright, and usage; it contains no GPS data.

## Generate local derivatives

`scripts/generate_photography.py` requires a private source map whose `sources`
object maps stable photo IDs to local source filenames. Keep that map and the
generated provenance manifest outside the repository.

```sh
python3 scripts/generate_photography.py \
  --source /path/to/private-masters \
  --source-map /path/to/private-source-map.json \
  --private-manifest /path/to/private-provenance.json
```

## Produce a production manifest

After the matching versioned derivatives exist locally, generate an R2-backed
manifest without reprocessing masters:

```sh
python3 scripts/generate_photography.py \
  --manifest-only \
  --asset-mode production \
  --asset-base https://images.example.com/photography/derivatives \
  --manifest-output /path/outside/repository/photos.production.json
```

Never publish the private provenance file: it contains source paths, hashes, and
private R2 master keys. Do not commit generated JPEGs. See
`docs/photography-cloudflare.md` for the two-bucket production design and staged
migration procedure.
