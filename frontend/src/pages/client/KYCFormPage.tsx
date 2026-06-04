import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { clientsApi } from '@/services/api';
import { CheckCircle, AlertCircle, ChevronRight, ChevronLeft } from 'lucide-react';

const STEPS = ['Personal Info', 'Financial Profile', 'Transaction Expectations', 'Declarations'];

const INCOME_RANGES = ['Under $30,000', '$30,000 - $75,000', '$75,000 - $150,000', 'Over $150,000'];
const FUND_SOURCES = ['Employment/Salary', 'Business Income', 'Investments', 'Inheritance', 'Property Sale', 'Other'];
const ID_TYPES = ['Passport', 'National ID Card', "Driver's License", 'Residence Permit'];

export default function KYCFormPage() {
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [existingProfile, setExistingProfile] = useState<any>(null);

  const { register, handleSubmit, getValues, formState: { errors } } = useForm();

  useEffect(() => {
    clientsApi.getMyProfile()
      .then(r => setExistingProfile(r.data))
      .catch(() => {});
  }, []);

  const onSubmit = async (data: any) => {
    setSubmitting(true);
    setError('');
    try {
      if (existingProfile) {
        await clientsApi.updateMyProfile(data);
      } else {
        await clientsApi.createProfile(data);
      }
      setSubmitted(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="card p-10 max-w-md">
          <CheckCircle className="mx-auto h-16 w-16 text-emerald-500" />
          <h2 className="mt-4 text-2xl font-bold text-gray-900">KYC Submitted!</h2>
          <p className="mt-2 text-gray-500">
            Your KYC application has been submitted for review. You'll receive a notification within 1-2 business days.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">KYC Verification Form</h1>
        <p className="mt-1 text-sm text-gray-500">Complete all sections to submit for review</p>
      </div>

      {/* Progress */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center gap-1">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold
                  ${i < step ? 'bg-emerald-500 text-white' : i === step ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'}`}>
                  {i < step ? '✓' : i + 1}
                </div>
                <span className={`text-xs hidden sm:block ${i === step ? 'font-medium text-primary' : 'text-gray-400'}`}>{s}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 mx-2 ${i < step ? 'bg-emerald-500' : 'bg-gray-200'}`} />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="card p-6 space-y-4">
          {/* Step 0: Personal */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Personal Information</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  { name: 'first_name', label: 'First Name', required: true },
                  { name: 'last_name', label: 'Last Name', required: true },
                  { name: 'middle_name', label: 'Middle Name' },
                  { name: 'date_of_birth', label: 'Date of Birth', type: 'date', required: true },
                  { name: 'phone_number', label: 'Phone Number', required: true },
                ].map(({ name, label, type = 'text', required }) => (
                  <div key={name}>
                    <label className="block text-sm font-medium text-gray-700">{label}{required && ' *'}</label>
                    <input {...register(name, { required: required ? `${label} is required` : false })}
                      type={type}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none" />
                    {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name]?.message as string}</p>}
                  </div>
                ))}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">ID Type *</label>
                  <select {...register('id_type', { required: 'ID type is required' })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
                    <option value="">Select...</option>
                    {ID_TYPES.map(t => <option key={t} value={t.toLowerCase().replace(/ /g, '_')}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">ID Number *</label>
                  <input {...register('id_number', { required: 'ID number is required' })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Address</label>
                  <input {...register('address_line1')} placeholder="Street address"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">City</label>
                  <input {...register('city')}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Financial */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Financial Profile</h2>
              {[
                { name: 'occupation', label: 'Occupation / Job Title', required: true },
                { name: 'employer_name', label: 'Employer / Company Name' },
              ].map(({ name, label, required }) => (
                <div key={name}>
                  <label className="block text-sm font-medium text-gray-700">{label}</label>
                  <input {...register(name, { required: required ? `${label} is required` : false })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700">Annual Income Range *</label>
                <select {...register('annual_income_range', { required: true })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
                  <option value="">Select range...</option>
                  {INCOME_RANGES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Primary Source of Funds *</label>
                <select {...register('source_of_funds', { required: true })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
                  <option value="">Select...</option>
                  {FUND_SOURCES.map(s => <option key={s} value={s.toLowerCase().replace(/ /g, '_')}>{s}</option>)}
                </select>
              </div>
            </div>
          )}

          {/* Step 2: Transaction expectations */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Transaction Expectations</h2>
              <div>
                <label className="block text-sm font-medium text-gray-700">Expected Monthly Transaction Volume (USD)</label>
                <input {...register('expected_monthly_transaction_volume', { valueAsNumber: true })}
                  type="number" min="0"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Purpose of Account</label>
                <textarea {...register('purpose_of_account')} rows={3}
                  placeholder="Describe the intended use of this account..."
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
              </div>
            </div>
          )}

          {/* Step 3: Declarations */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Declarations</h2>
              {[
                { name: 'is_pep', label: 'I am or have been a Politically Exposed Person (PEP)' },
                { name: 'is_us_person', label: 'I am a US person for tax purposes' },
                { name: 'is_beneficial_owner', label: 'I am the beneficial owner of this account', defaultValue: true },
              ].map(({ name, label }) => (
                <label key={name} className="flex items-start gap-3 cursor-pointer">
                  <input {...register(name)} type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary" />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
              <div className="rounded-lg bg-blue-50 p-4 mt-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input {...register('agrees_to_terms', { required: 'You must agree to proceed' })} type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary" />
                  <span className="text-sm text-gray-700">
                    I confirm that all information provided is accurate and complete. I agree to the Terms of Service and Privacy Policy. *
                  </span>
                </label>
                {errors.agrees_to_terms && <p className="mt-1 text-xs text-red-600">{errors.agrees_to_terms.message as string}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between mt-4">
          <button type="button" onClick={() => setStep(s => s - 1)} disabled={step === 0}
            className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40">
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          {step < STEPS.length - 1 ? (
            <button type="button" onClick={() => setStep(s => s + 1)}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
              Next <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button type="submit" disabled={submitting}
              className="rounded-lg bg-emerald-600 px-6 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
              {submitting ? 'Submitting...' : 'Submit KYC Application'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
