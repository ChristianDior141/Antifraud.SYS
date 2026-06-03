import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { login } from '@/store/slices/authSlice';
import type { AppDispatch, RootState } from '@/store';
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react';

const schema = z.object({
  email: z.string().email('Valid email required'),
  password: z.string().min(1, 'Password required'),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading } = useSelector((s: RootState) => s.auth);
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setError('');
    const result = await dispatch(login(data));
    if (login.fulfilled.match(result)) {
      navigate('/dashboard');
    } else {
      setError(result.payload as string);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left panel */}
      <div className="hidden w-1/2 flex-col justify-between bg-gradient-to-br from-blue-600 to-blue-800 p-12 lg:flex">
        <div className="flex items-center gap-3 text-white">
          <Shield className="h-8 w-8" />
          <span className="text-xl font-bold">KYC/AML Platform</span>
        </div>
        <div className="text-white">
          <h1 className="text-4xl font-bold leading-tight">
            Secure KYC &amp; AML<br />Compliance Platform
          </h1>
          <p className="mt-4 text-lg text-blue-200">
            Automated customer risk assessment and AML monitoring for modern financial institutions.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-4">
            {[
              { label: 'Clients Verified', value: '50,000+' },
              { label: 'AML Alerts Processed', value: '12,000+' },
              { label: 'Risk Accuracy', value: '99.2%' },
              { label: 'Processing Time', value: '<24h' },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-white/10 p-4">
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="text-sm text-blue-200">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="text-sm text-blue-300">© 2025 KYC/AML Platform. All rights reserved.</p>
      </div>

      {/* Right panel */}
      <div className="flex flex-1 items-center justify-center bg-gray-50 px-6 py-12">
        <div className="w-full max-w-md">
          <div className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
            <div className="mb-8 text-center lg:hidden">
              <Shield className="mx-auto h-10 w-10 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Sign in to your account</h2>
            <p className="mt-1 text-sm text-gray-500">Enter your credentials to access the platform</p>

            {error && (
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email address</label>
                <input
                  {...register('email')}
                  type="email"
                  placeholder="you@company.com"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Password</label>
                <div className="relative mt-1">
                  <input
                    {...register('password')}
                    type={showPass ? 'text' : 'password'}
                    placeholder="••••••••"
                    className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 pr-10 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <button type="button" onClick={() => setShowPass(!showPass)}
                    className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600">
                    {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="mt-6 rounded-lg bg-gray-50 p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase">Demo credentials</p>
              <div className="mt-2 space-y-1 text-xs text-gray-600">
                <p><span className="font-medium">Admin:</span> admin@kyc-platform.com / Admin123!@#</p>
                <p><span className="font-medium">Compliance:</span> compliance1@kyc-platform.com / Admin123!@#</p>
                <p><span className="font-medium">Analyst:</span> analyst1@kyc-platform.com / Admin123!@#</p>
              </div>
            </div>

            <p className="mt-6 text-center text-sm text-gray-500">
              Don't have an account?{' '}
              <Link to="/register" className="font-medium text-primary hover:underline">Register</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
