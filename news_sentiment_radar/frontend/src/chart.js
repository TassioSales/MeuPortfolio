export function drawSentimentChart(canvas, counts) {
  const ctx = canvas.getContext("2d");
  const total = Math.max(1, Object.values(counts).reduce((sum, value) => sum + value, 0));
  const slices = [
    { label: "positivo", value: counts.positivo || 0, color: "#86efac" },
    { label: "neutro", value: counts.neutro || 0, color: "#fde047" },
    { label: "negativo", value: counts.negativo || 0, color: "#fb7185" },
  ];

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  let start = -Math.PI / 2;
  const centerX = canvas.width / 2;
  const centerY = 116;
  const radius = 86;

  for (const slice of slices) {
    const angle = (slice.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = slice.color;
    ctx.shadowBlur = 18;
    ctx.shadowColor = slice.color;
    ctx.fill();
    start += angle;
  }

  ctx.shadowBlur = 0;
  ctx.fillStyle = "#08090f";
  ctx.beginPath();
  ctx.arc(centerX, centerY, 48, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#f8fafc";
  ctx.font = "900 26px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(String(total), centerX, centerY + 8);

  ctx.font = "800 13px Inter, system-ui, sans-serif";
  slices.forEach((slice, index) => {
    const y = 236 + index * 20;
    ctx.fillStyle = slice.color;
    ctx.fillRect(42, y - 10, 10, 10);
    ctx.fillStyle = "#94a3b8";
    ctx.textAlign = "left";
    ctx.fillText(`${slice.label}: ${slice.value}`, 60, y);
  });
}

export function drawTimelineChart(canvas, articles) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const buckets = buildHourlyBuckets(articles);
  const maxVolume = Math.max(1, ...buckets.map((bucket) => bucket.count));
  const plot = { x: 44, y: 24, w: width - 72, h: height - 64 };

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = plot.y + (plot.h / 4) * i;
    ctx.beginPath();
    ctx.moveTo(plot.x, y);
    ctx.lineTo(plot.x + plot.w, y);
    ctx.stroke();
  }

  buckets.forEach((bucket, index) => {
    const barW = plot.w / buckets.length - 6;
    const x = plot.x + index * (plot.w / buckets.length) + 3;
    const barH = (bucket.count / maxVolume) * plot.h;
    const y = plot.y + plot.h - barH;
    const tone = bucket.score > 0 ? "#86efac" : bucket.score < 0 ? "#fb7185" : "#fde047";

    ctx.fillStyle = "rgba(148, 163, 184, 0.16)";
    ctx.fillRect(x, plot.y, barW, plot.h);
    ctx.fillStyle = tone;
    ctx.shadowBlur = 14;
    ctx.shadowColor = tone;
    ctx.fillRect(x, y, barW, barH);
    ctx.shadowBlur = 0;

    if (index % 2 === 0) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "700 11px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(bucket.label, x + barW / 2, height - 18);
    }
  });
}

function buildHourlyBuckets(articles) {
  const now = new Date();
  const buckets = Array.from({ length: 12 }, (_, index) => {
    const date = new Date(now.getTime() - (11 - index) * 60 * 60 * 1000);
    return {
      hour: date.getHours(),
      label: `${String(date.getHours()).padStart(2, "0")}h`,
      count: 0,
      score: 0,
    };
  });

  articles.forEach((article) => {
    const date = new Date(article.publishedAt);
    const diffHours = Math.floor((now.getTime() - date.getTime()) / 3_600_000);
    if (diffHours < 0 || diffHours > 11) {
      return;
    }
    const bucket = buckets[11 - diffHours];
    bucket.count += 1;
    bucket.score += article.score;
  });

  return buckets;
}
