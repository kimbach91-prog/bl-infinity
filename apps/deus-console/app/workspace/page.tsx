import { redirect } from 'next/navigation';
import { canAccessSurface, loadVerifiedAccessContext } from '../../lib/session';

export const dynamic = 'force-dynamic';

const surfaces = [
  ['Nhiệm vụ', 'Các mục tiêu đang được giao và trạng thái xử lý'],
  ['Bằng chứng', 'Nguồn, receipt và dữ kiện cần thiết cho quyết định'],
  ['Kết quả', 'Đầu ra đã qua lớp projection dành cho người dùng'],
  ['Hành động', 'Các thao tác được phép trong phạm vi vai trò hiện tại'],
  ['Ẩn số', 'Những điều chưa đủ bằng chứng hoặc còn mâu thuẫn'],
];

export default async function WorkspacePage() {
  const context = await loadVerifiedAccessContext();
  if (!context || !canAccessSurface(context, 'hmi:workspace:read')) redirect('/login');

  const { session } = context;

  return (
    <main className="workspace-shell">
      <aside className="sidebar">
        <div className="brand">DEUS</div>
        <div className="tenant-pill">{session.tenantKind === 'government' ? 'GOVERNMENT' : 'ENTERPRISE'}</div>
        <nav>
          {surfaces.map(([title]) => (
            <a key={title} href={`#${title}`}>{title}</a>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span>{session.displayName ?? session.identityId}</span>
          <small>{session.tenantId}</small>
        </div>
      </aside>

      <section className="workspace-main">
        <header className="workspace-header">
          <div>
            <div className="eyebrow">SOVEREIGN WORK INTERFACE</div>
            <h1>Không gian làm việc</h1>
          </div>
          <div className="secure-badge">Projection-only session</div>
        </header>

        <section className="hero-panel">
          <div>
            <span className="label">Trạng thái</span>
            <strong>Sẵn sàng nhận nhiệm vụ</strong>
          </div>
          <p>
            Giao diện này chỉ hiển thị dữ liệu đã được cho phép theo tenant, vai trò và phân loại. Lõi nội bộ không có đường đọc trực tiếp từ workspace.
          </p>
        </section>

        <section className="grid">
          {surfaces.map(([title, description]) => (
            <article className="surface-card" id={title} key={title}>
              <span className="label">{title}</span>
              <h2>{description}</h2>
              <p>Chưa có projection dữ liệu trực tiếp được kết nối cho phiên này.</p>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
