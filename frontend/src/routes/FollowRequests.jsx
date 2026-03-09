import AppShell from '../components/layout/AppShell.jsx'
import FollowRequestsPanel from '../components/FollowRequestsPanel.jsx'

export default function FollowRequests() {
  return (
    <AppShell right={null}>
      <div style={{ padding: 24 }}>
        <FollowRequestsPanel />
      </div>
    </AppShell>
  )
}
