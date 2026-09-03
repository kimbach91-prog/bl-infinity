export default async function handler(req, res) {
  res.status(200).json({
    ok: true,
    service: "BL Compute Federation Control Plane",
    version: "0.1.0",
    time: new Date().toISOString()
  });
}
