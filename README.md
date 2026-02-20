# eink-dither

Flask-based image processor that converts arbitrary images to indexed grayscale PNGs with dither (default: 8 levels / 3-bit), caches results, and serves ETag/Cache-Control headers.

- Endpoint: `/process?url=<source_url>&levels=8`
- Default levels: 8 (3-bit). No resizing — original image dimensions are preserved.

Usage
1. Build & run locally:
   - docker build -t eink-dither .
   - docker run -p 8080:8080 -v $(pwd)/data/cache:/data/cache eink-dither

2. Docker Compose:
   - docker-compose up -d

3. GitHub Actions multi-arch build:
   - Add repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.
   - Create a release tag like `v1.0.0` and push — the workflow will build and push multi-arch images.

ESPHome usage
- Point `online_image` at this service:
```yaml
online_image:

- id: my_eink_img
    url: &quot;http://your-host:8080/process?url=https://example.com/image.png&amp;levels=8&quot;
    transparency: opaque
