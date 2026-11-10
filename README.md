# Fonts

The render script embeds two subset fonts as base64 WOFF data URIs. Add:

- `fonts/serif-400.woff`: Instrument Serif, Regular (upright, not Italic)
- `fonts/sans-400.woff`: Geist, Regular

Make the subsets (needs `pip install fonttools brotli`):

    pyftsubset InstrumentSerif-Regular.ttf --unicodes="U+0020-007E,U+2190-2193" --flavor=woff --output-file=fonts/serif-400.woff
    pyftsubset Geist-Regular.ttf --unicodes="U+0020-007E,U+2190-2193" --flavor=woff --output-file=fonts/sans-400.woff

Check the file name table before you trust a download. Google can serve the Italic under the Regular name.

If the files are missing, the cards fall back to Georgia and Helvetica.
