import React, { useState } from 'react';
import { useConnectionsList, useConnectionMutations } from '../../hooks/useConnections';
import { useToast } from '../../components/ui/ToastProvider';
import { DataTable } from '../../components/ui/DataTable';
import { DrawerPanel } from '../../components/ui/DrawerPanel';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { ErrorBanner } from '../../components/ui/ErrorBanner';
import { formatTimeAgo } from '../../utils/formatters';
import { useForm } from 'react-hook-form';
import {
  TabList,
  Tab,
  Button,
  Spinner,
  Field,
  Input,
  Select,
  Checkbox,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
} from '@fluentui/react-components';
import { Database, Plus, Trash2, ShieldAlert } from 'lucide-react';

export const ConnectionsPage = () => {
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState('Oracle');
  
  // Connection drawer control
  const [drawerOpen, setDrawerOpen] = useState(false);
  
  // Delete confirm dialog control
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [connectionToDelete, setConnectionToDelete] = useState(null);

  // Test connection feedback state
  const [testResult, setTestResult] = useState(null);

  // Fetch connections for the active tab database engine
  const { data: connections = [], isLoading, isError } = useConnectionsList(activeTab);

  // Mutations
  const {
    createConnection,
    isCreating,
    deleteConnection: performDelete,
    isDeleting,
    testConnection,
    isTesting,
  } = useConnectionMutations(activeTab);

  // Form hooks
  const { register, handleSubmit, reset, watch } = useForm();

  // Watchers for dynamic form elements
  const oracleType = watch('oracleType', 'service');
  const useWindowsAuth = watch('use_windows_auth', false);

  // Triggered when DB Engine tab is clicked
  const handleTabChange = (dbType) => {
    setActiveTab(dbType);
    setTestResult(null);
    reset();
  };

  const handleOpenDrawer = () => {
    setTestResult(null);
    reset({
      port: getDefaultPort(activeTab),
      oracleType: 'service',
      sslmode: 'disable',
      protocol: 'mongodb',
      auth_source: 'admin',
      use_windows_auth: false,
    });
    setDrawerOpen(true);
  };

  const getDefaultPort = (type) => {
    switch (type) {
      case 'Oracle': return 1521;
      case 'PostgreSQL': return 5432;
      case 'MySQL': return 3306;
      case 'MSSQL': return 1433;
      case 'MongoDB': return 27017;
      case 'ClickHouse': return 8123;
    }
  };

  // Test connection function
  const handleTestConnection = async () => {
    const values = watch();
    setTestResult(null);
    try {
      const payload = {
        host: values.host,
        port: Number(values.port),
        username: values.username,
        password: values.password,
      };

      if (activeTab === 'Oracle') {
        if (values.oracleType === 'service') {
          payload.service_name = values.service_name;
        } else {
          payload.sid = values.sid;
        }
      } else if (activeTab === 'PostgreSQL') {
        payload.database = values.database;
        payload.sslmode = values.sslmode;
      } else if (activeTab === 'MongoDB') {
        payload.database = values.database;
        payload.protocol = values.protocol;
        payload.auth_source = values.auth_source;
        payload.replica_set = values.replica_set || undefined;
      } else if (activeTab === 'MSSQL') {
        payload.database = values.database;
        payload.use_windows_auth = values.use_windows_auth;
      } else {
        // MySQL, ClickHouse
        payload.database = values.database;
        if (activeTab === 'ClickHouse') {
          payload.protocol = values.protocol || 'http';
        }
      }

      const res = await testConnection(payload);
      setTestResult({
        success: res.success,
        message: res.message,
      });
      if (res.success) {
        addToast(`Connection to ${values.name || 'database'} verified successfully!`, 'success');
      } else {
        addToast(`Verification failed: ${res.message}`, 'error');
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err.response?.data?.message || err.message || 'Network error occurred testing credentials.',
      });
      addToast('Error verifying credentials.', 'error');
    }
  };

  // Save connection Profile
  const handleSaveConnection = async (data) => {
    try {
      const payload = { ...data, port: Number(data.port) };
      await createConnection(payload);
      addToast(`Connection profile "${data.name}" added successfully.`, 'success');
      setDrawerOpen(false);
      reset();
    } catch (err) {
      addToast(err.response?.data?.message || err.message || 'Failed to save connection profile.', 'error');
    }
  };

  // Delete Action Trigger
  const handleConfirmDelete = (conn) => {
    setConnectionToDelete(conn);
    setDeleteDialogOpen(true);
  };

  const executeDelete = async () => {
    if (!connectionToDelete) return;
    try {
      await performDelete(connectionToDelete.id);
      addToast(`Connection profile "${connectionToDelete.name}" deleted successfully.`, 'success');
    } catch (err) {
      addToast(err.response?.data?.message || err.message || 'Failed to delete connection profile.', 'error');
    } finally {
      setConnectionToDelete(null);
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Profile Name',
      sortable: true,
      render: (c) => <span className="font-semibold text-brand-text-primary">{c.name}</span>,
    },
    {
      key: 'host',
      label: 'Host Address',
      render: (c) => `${c.host}:${c.port}`,
    },
    {
      key: 'database',
      label: 'Target DB / Schema',
      render: (c) => {
        if (activeTab === 'Oracle') {
          return c.service_name ? `Service: ${c.service_name}` : `SID: ${c.sid}`;
        }
        return c.database || '-';
      },
    },
    {
      key: 'username',
      label: 'Connect User',
    },
    {
      key: 'created_at',
      label: 'Added Date',
      sortable: true,
      render: (c) => formatTimeAgo(c.created_at),
    },
    {
      key: 'actions',
      label: 'Actions',
      headerClassName: 'text-right',
      cellClassName: 'text-right',
      render: (c) => (
        <Button
          icon={<Trash2 className="h-4 w-4" />}
          appearance="subtle"
          onClick={() => handleConfirmDelete(c)}
          className="text-brand-error hover:bg-red-50"
          title="Delete Connection"
        />
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Title block */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-text-primary">Database Connections</h1>
          <p className="text-sm text-brand-text-secondary">
            Manage target database endpoints for ActMon telemetry gathering agents.
          </p>
        </div>
        <div>
          <Button
            appearance="primary"
            icon={<Plus className="h-4 w-4" />}
            onClick={handleOpenDrawer}
            disabled={activeTab === 'MSSQL' && isError} // Disable if API failed on MSSQL tab
          >
            Add Connection
          </Button>
        </div>
      </div>

      {/* Tabs list selecting DB engine */}
      <TabList selectedValue={activeTab} onTabSelect={(_, d) => handleTabChange(d.value)}>
        <Tab id="Oracle" value="Oracle">Oracle</Tab>
        <Tab id="PostgreSQL" value="PostgreSQL">PostgreSQL</Tab>
        <Tab id="MySQL" value="MySQL">MySQL</Tab>
        <Tab id="MSSQL" value="MSSQL">MSSQL</Tab>
        <Tab id="MongoDB" value="MongoDB">MongoDB</Tab>
        <Tab id="ClickHouse" value="ClickHouse">ClickHouse</Tab>
      </TabList>

      {/* MSSQL Fallback Warning Banner if MSSQL fails */}
      {activeTab === 'MSSQL' && isError ? (
        <div className="space-y-4">
          <ErrorBanner
            title="MSSQL Warning"
            message="MSSQL connection management is temporarily unavailable. Please check server logs."
          />
          <div className="p-8 border border-dashed border-brand-border rounded-card bg-white flex flex-col items-center justify-center text-center">
            <ShieldAlert className="h-12 w-12 text-amber-500 mb-2" />
            <h3 className="font-semibold text-brand-text-primary">MSSQL Endpoint Blocked</h3>
            <p className="text-xs text-brand-text-secondary max-w-sm mt-1">
              The backend service encountered errors loading the SQL Server integration driver. Admin operations are locked.
            </p>
          </div>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center items-center py-20">
          <Spinner size="large" label="Querying connection profiles..." />
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={connections}
          rowKeyField="id"
          emptyState={
            <div className="text-center py-12 text-brand-text-secondary flex flex-col items-center justify-center gap-2">
              <Database className="h-10 w-10 text-gray-300" />
              <p className="font-semibold">No Connection Profiles Added</p>
              <p className="text-xs">Click "Add Connection" to register your first {activeTab} target.</p>
            </div>
          }
        />
      )}

      {/* Add Connection Drawer Panel */}
      <DrawerPanel
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={`Add ${activeTab} Connection`}
      >
        <form onSubmit={handleSubmit(handleSaveConnection)} className="space-y-4">
          <Field label="Connection Name" required>
            <Input {...register('name', { required: true })} placeholder="e.g. Production Oracle DB" />
          </Field>

          {activeTab === 'MongoDB' && (
            <Field label="Protocol" required>
              <Select {...register('protocol')}>
                <option value="mongodb">mongodb:// (Standard)</option>
                <option value="mongodb+srv">mongodb+srv:// (DNS Seed List)</option>
              </Select>
            </Field>
          )}

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <Field label="Host Address" required>
                <Input {...register('host', { required: true })} placeholder="e.g. 10.0.1.25" />
              </Field>
            </div>
            <div>
              <Field label="Port" required>
                <Input {...register('port', { required: true })} type="number" />
              </Field>
            </div>
          </div>

          {activeTab === 'Oracle' && (
            <div className="space-y-4">
              <Field label="Connection Identifier">
                <Select {...register('oracleType')}>
                  <option value="service">Service Name</option>
                  <option value="sid">SID (System Identifier)</option>
                </Select>
              </Field>
              {oracleType === 'service' ? (
                <Field label="Service Name" required>
                  <Input {...register('service_name', { required: oracleType === 'service' })} placeholder="e.g. orcl.local" />
                </Field>
              ) : (
                <Field label="SID" required>
                  <Input {...register('sid', { required: oracleType === 'sid' })} placeholder="e.g. ORCL" />
                </Field>
              )}
            </div>
          )}

          {activeTab !== 'Oracle' && (
            <Field label="Database Name" required>
              <Input {...register('database', { required: activeTab !== 'MSSQL' || !useWindowsAuth })} placeholder="e.g. actmon_telemetry" />
            </Field>
          )}

          {activeTab === 'PostgreSQL' && (
            <Field label="SSL Mode">
              <Select {...register('sslmode')}>
                <option value="disable">Disable</option>
                <option value="allow">Allow</option>
                <option value="prefer">Prefer</option>
                <option value="require">Require</option>
                <option value="verify-ca">Verify CA</option>
                <option value="verify-full">Verify Full</option>
              </Select>
            </Field>
          )}

          {activeTab === 'ClickHouse' && (
            <Field label="Protocol">
              <Select {...register('protocol')}>
                <option value="http">HTTP (8123)</option>
                <option value="native">Native TCP (9000)</option>
              </Select>
            </Field>
          )}

          {activeTab === 'MongoDB' && (
            <>
              <Field label="Auth Source">
                <Input {...register('auth_source')} placeholder="e.g. admin" />
              </Field>
              <Field label="Replica Set (Optional)">
                <Input {...register('replica_set')} placeholder="e.g. rs0" />
              </Field>
            </>
          )}

          {activeTab === 'MSSQL' && (
            <div className="py-2">
              <Checkbox {...register('use_windows_auth')} label="Use Windows Authentication" />
            </div>
          )}

          {/* Credentials */}
          {(!useWindowsAuth || activeTab !== 'MSSQL') && (
            <div className="grid grid-cols-2 gap-4">
              <Field label="Username" required>
                <Input {...register('username', { required: true })} placeholder="Username" />
              </Field>
              <Field label="Password">
                <Input {...register('password')} type="password" placeholder="Password" />
              </Field>
            </div>
          )}

          {/* Verification alert message */}
          {testResult && (
            <MessageBar intent={testResult.success ? 'success' : 'error'} className="mt-2">
              <MessageBarBody>
                <MessageBarTitle>{testResult.success ? 'Credentials OK' : 'Verification Failed'}</MessageBarTitle>
                {testResult.message}
              </MessageBarBody>
            </MessageBar>
          )}

          {/* Drawer Actions */}
          <div className="flex gap-2 pt-6 justify-end border-t border-brand-border mt-6">
            <Button
              type="button"
              appearance="secondary"
              onClick={handleTestConnection}
              disabled={isTesting || isCreating}
            >
              {isTesting ? <Spinner size="tiny" label="Verifying..." /> : 'Test Connection'}
            </Button>
            <Button
              type="submit"
              appearance="primary"
              disabled={isTesting || isCreating}
            >
              {isCreating ? <Spinner size="tiny" label="Saving..." /> : 'Save Profile'}
            </Button>
          </div>
        </form>
      </DrawerPanel>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Connection Profile"
        message={`Are you sure you want to delete the database connection profile "${connectionToDelete?.name}"? ActMon agents will no longer poll telemetry from this endpoint.`}
        confirmLabel={isDeleting ? 'Deleting...' : 'Delete'}
        onConfirm={executeDelete}
        isDanger={true}
      />
    </div>
  );
};
