export const dynamic = 'force-dynamic';

export default function LoginPage() {
  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="eyebrow">DEUS · CONTROLLED ACCESS</div>
        <h1>Truy cập do tổ chức quản lý</h1>
        <p>
          DEUS chỉ dành cho tổ chức doanh nghiệp và cơ quan nhà nước đã được cấp quyền. Không có đăng ký công khai,
          tài khoản khách hoặc chế độ truy cập ẩn danh.
        </p>
        <div className="login-status">
          <span className="status-dot" />
          Chưa có phiên đăng nhập hợp lệ
        </div>
        <p className="muted">
          Hãy sử dụng cổng SSO, passkey, smart card hoặc phương thức xác thực do đơn vị của bạn cung cấp.
        </p>
      </section>
    </main>
  );
}
