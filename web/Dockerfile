FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json /ui/package.json
RUN npm install
COPY ui /ui
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
RUN pip install --no-cache-dir .
COPY --from=ui /ui/dist /app/ui/dist
ENV UI_DIST=/app/ui/dist
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
