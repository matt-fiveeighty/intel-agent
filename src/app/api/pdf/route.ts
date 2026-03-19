import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { writeFile, readFile, unlink } from "fs/promises";
import path from "path";
import os from "os";

export async function POST(req: NextRequest) {
  const data = await req.json();
  const tmpDir = os.tmpdir();
  const dataFile = path.join(tmpDir, `intel-data-${Date.now()}.json`);
  const pdfFile = path.join(tmpDir, `intel-report-${Date.now()}.pdf`);
  const scriptPath = path.join(process.cwd(), "scripts", "build_report.py");

  await writeFile(dataFile, JSON.stringify(data));

  try {
    await new Promise<void>((resolve, reject) => {
      execFile(
        "python3",
        [scriptPath, dataFile, pdfFile],
        { timeout: 60000 },
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });

    const pdfBuffer = await readFile(pdfFile);
    const brand = (data.brand as string) ?? "report";

    await Promise.all([unlink(dataFile), unlink(pdfFile)]);

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${brand
          .replace(/[^a-z0-9]/gi, "-")
          .toLowerCase()}-ad-intelligence.pdf"`,
      },
    });
  } catch (err) {
    await unlink(dataFile).catch(() => null);
    await unlink(pdfFile).catch(() => null);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
