import { useEffect, useState, type FormEvent } from "react";
import { api } from "../services/api";
import type { Invitation, StaffAccount } from "../types";

export function StaffPage() {
  const [staff, setStaff] = useState<StaffAccount[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [roles, setRoles] = useState<{ role: string; permissions: string[] }[]>([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("");
  const [invitationUrl, setInvitationUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const [staffList, invitationList, roleList] = await Promise.all([
        api.staff(), api.invitations(), api.roles(),
      ]);
      setStaff(staffList);
      setInvitations(invitationList);
      setRoles(roleList.filter((item) => item.role !== "owner"));
      setRole((current) => current || roleList.find((item) => item.role === "operations_manager")?.role || "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load staff access.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setInvitationUrl("");
    try {
      const result = await api.invite({ email, full_name: fullName, role });
      if (!result.invitation_token) throw new Error("The API did not return the one-time invitation token.");
      setInvitationUrl(`${window.location.origin}/invite?token=${encodeURIComponent(result.invitation_token)}`);
      setEmail("");
      setFullName("");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not create staff invitation.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <header className="page-heading"><div><span className="kicker">ACCESS CONTROL</span><h1>Staff and invitations</h1>
        <p>Staff access is role-based and invitation-only. New users must set a password and enroll MFA before activation.</p></div></header>
      <form className="panel invite-form" onSubmit={invite}>
        <h2>Invite a staff member</h2>
        <label>Full name<input required minLength={2} maxLength={100} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
        <label>Work email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Role<select required value={role} onChange={(event) => setRole(event.target.value)}>
          {roles.map((item) => <option key={item.role} value={item.role}>{item.role.replaceAll("_", " ")}</option>)}
        </select></label>
        <button disabled={loading || !role} type="submit">{loading ? "Creating…" : "Create invitation"}</button>
        {invitationUrl && <p className="notice">Invitation created. Copy this one-time link and deliver it through an approved private channel; no email was sent. <a href={invitationUrl}>{invitationUrl}</a></p>}
        {error && <p className="error" role="alert">{error}</p>}
      </form>
      <section className="panel"><h2>Staff accounts</h2><div className="table-scroll"><table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>MFA</th><th>Created</th></tr></thead>
        <tbody>{staff.map((item) => <tr key={item.id}><td>{item.full_name}</td><td>{item.email}</td><td>{item.role.replaceAll("_", " ")}</td><td>{item.status}</td><td>{item.mfa_enabled ? "Enabled" : "Not enrolled"}</td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>)}
          {!staff.length && <tr><td className="empty-cell" colSpan={6}>No staff accounts were returned.</td></tr>}</tbody>
      </table></div></section>
      <section className="panel"><h2>Invitation history</h2><div className="table-scroll"><table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Issued</th><th>Expires</th><th>Status</th></tr></thead>
        <tbody>{invitations.map((item) => <tr key={item.id}><td>{item.full_name}</td><td>{item.email}</td><td>{item.role.replaceAll("_", " ")}</td><td>{new Date(item.created_at).toLocaleString()}</td><td>{new Date(item.expires_at).toLocaleString()}</td><td>{item.accepted_at ? "Accepted" : new Date(item.expires_at) < new Date() ? "Expired" : "Pending"}</td></tr>)}
          {!invitations.length && <tr><td className="empty-cell" colSpan={6}>No invitations yet.</td></tr>}</tbody>
      </table></div></section>
    </section>
  );
}
