import { expect,it,vi } from 'vitest';
import { render,screen,fireEvent,waitFor } from '@testing-library/react';
import { QueryClient,QueryClientProvider } from '@tanstack/react-query';
import CatalogSetupControl from './CatalogSetupControl';
import { api } from '@/api';
vi.mock('@/api',()=>({api:{get:vi.fn(),post:vi.fn()}}));
vi.mock('react-i18next',()=>({useTranslation:()=>({t:key=>key,i18n:{language:'en'}})}));
it('shows the server preview and saves only after explicit confirmation',async()=>{
 api.get.mockResolvedValue({data:{snapshot:'a'.repeat(64),create_plans:[{name:'professional',price:400,max_users:5,ai_daily_limit:10}],preserved_plans:[{id:3,name:'pro',price:1000}],conflicts:[]}});
 api.post.mockResolvedValue({data:{created_plans:['professional']}});
 const saved=vi.fn();render(<QueryClientProvider client={new QueryClient()}><CatalogSetupControl onApplied={saved}/></QueryClientProvider>);
 fireEvent.change(screen.getByLabelText('Setup reason'),{target:{value:'Owner reviewed the setup'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview approved catalog setup'}));
 expect(await screen.findByText(/professional.*400/)).toBeInTheDocument();
 expect(screen.getByText(/pro.*1000/)).toBeInTheDocument();
 expect(api.post).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Review and confirm setup'}));
 fireEvent.click(await screen.findByRole('button',{name:'Confirm setup'}));
 await waitFor(()=>expect(api.post).toHaveBeenCalledWith('/api/v1/admin/subscriptions/catalog-setup',{expected_snapshot:'a'.repeat(64),reason:'Owner reviewed the setup'}));
 await waitFor(()=>expect(saved).toHaveBeenCalledOnce());
});

it('blocks conflicting catalog changes',async()=>{
 api.post.mockClear();
 api.get.mockResolvedValue({data:{snapshot:'b'.repeat(64),create_plans:[],preserved_plans:[],conflicts:[{plan_id:2,name:'professional',fields:['price']}]}});
 render(<QueryClientProvider client={new QueryClient()}><CatalogSetupControl/></QueryClientProvider>);
 fireEvent.change(screen.getByLabelText('Setup reason'),{target:{value:'Owner reviewed conflict'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview approved catalog setup'}));
 expect(await screen.findByRole('button',{name:'Review and confirm setup'})).toBeDisabled();
 expect(api.post).not.toHaveBeenCalled();
});

it('requires a fresh preview after a stale-state rejection',async()=>{
 api.post.mockClear();api.post.mockRejectedValue({response:{data:{detail:'Catalog changed; refresh preview'}}});
 api.get.mockResolvedValue({data:{snapshot:'c'.repeat(64),create_plans:[],preserved_plans:[],conflicts:[]}});
 const saved=vi.fn();render(<QueryClientProvider client={new QueryClient()}><CatalogSetupControl onApplied={saved}/></QueryClientProvider>);
 fireEvent.change(screen.getByLabelText('Setup reason'),{target:{value:'Owner reviewed stale preview'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview approved catalog setup'}));
 fireEvent.click(await screen.findByRole('button',{name:'Review and confirm setup'}));
 fireEvent.click(await screen.findByRole('button',{name:'Confirm setup'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Catalog changed');
 expect(screen.queryByRole('button',{name:'Review and confirm setup'})).not.toBeInTheDocument();
 expect(saved).not.toHaveBeenCalled();
});
