import { useState } from 'react';
import { ExternalLink, MapPin, Phone, Shield, Info } from 'lucide-react';
import { useMetrics } from '../context/MetricsContext';

interface Resource {
  name: string;
  description: string;
  phone?: string;
  website?: string;
  address?: string;
  available?: string;
}

const resources: Resource[] = [
  {
    name: "National Domestic Violence Hotline",
    description: "24/7 support, crisis intervention, and safety planning",
    phone: "1-800-799-7233",
    available: "24/7"
  },
  {
    name: "WEAVE (Women Escaping A Violent Environment)",
    description: "Emergency shelter, counseling, and support groups in Sacramento",
    phone: "916-920-2952",
    website: "weaveinc.org",
    available: "24/7 Crisis Line"
  },
  {
    name: "My Sister's House",
    description: "Transitional housing and supportive services",
    phone: "916-428-3271",
    website: "my-sisters-house.org"
  },
  {
    name: "SAFE Credit Union Convention Center - Family Justice Center",
    description: "Comprehensive services including legal, medical, and advocacy support",
    phone: "916-874-7233",
    website: "www.sacramentofjc.org"
  },
  {
    name: "Legal Services of Northern California",
    description: "Free legal assistance for survivors",
    phone: "916-551-2150",
    website: "lsnc.net"
  }
];

export function ResourcesSection() {
  const [showHowItWorks, setShowHowItWorks] = useState(false)
  const { recordResourceClick } = useMetrics()

  return (
    <div className="max-w-5xl mx-auto">

      {/* Privacy Reminder */}
      <div className="mb-10 p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-3">
        <Shield className="w-5 h-5 text-teal-600 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-medium text-teal-900">Your privacy matters</p>
          <p className="text-sm text-teal-700 mt-1">
            Guest conversations are never saved or stored. Signed-in users have
            conversation history saved securely. We never share your information
            with third parties. You can exit this site at any time using the
            Quick Exit button.
          </p>
        </div>
      </div>

      {/* How This Works */}
      <div className="mb-10 border border-gray-200 rounded-xl overflow-hidden">
        <button
          onClick={() => setShowHowItWorks(!showHowItWorks)}
          className="w-full flex items-center justify-between p-5 bg-white hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-2 text-gray-900 font-medium">
            <Info className="w-5 h-5 text-teal-600" />
            How CARE Bot works
          </div>
          <span className="text-gray-400 text-sm">{showHowItWorks ? '▲ Hide' : '▼ Show'}</span>
        </button>

        {showHowItWorks && (
          <div className="px-5 pb-5 bg-white border-t border-gray-100 space-y-4 text-sm text-gray-700">
            <div className="pt-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold shrink-0">1</span>
                <div>
                  <p className="font-medium text-gray-900">You ask a question or share how you're feeling</p>
                  <p className="text-gray-600 mt-0.5">CARE Bot listens without judgment and responds with care.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold shrink-0">2</span>
                <div>
                  <p className="font-medium text-gray-900">Responses are grounded in trusted resources</p>
                  <p className="text-gray-600 mt-0.5">CARE Bot uses trauma-informed documents like SAMHSA guidelines to provide accurate, compassionate information.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold shrink-0">3</span>
                <div>
                  <p className="font-medium text-gray-900">Crisis detection runs in the background</p>
                  <p className="text-gray-600 mt-0.5">If your message suggests you may be in crisis, CARE Bot will prioritize connecting you with immediate support resources.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold shrink-0">4</span>
                <div>
                  <p className="font-medium text-gray-900">CARE Bot is not a replacement for professional help</p>
                  <p className="text-gray-600 mt-0.5">It is a supportive tool. For emergencies, please call 911 or 988.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Resources */}
      <h2 className="text-3xl font-semibold text-gray-900 mb-8 text-center">
        Local Support Resources (Sacramento Area)
      </h2>

      <div className="grid md:grid-cols-2 gap-6">
        {resources.map((resource) => (
          <div
            key={resource.name}
            className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
          >
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{resource.name}</h3>
            <p className="text-gray-700 mb-4">{resource.description}</p>

            <div className="space-y-2">
              {resource.phone && (
                <div className="flex items-center gap-2 text-gray-800">
                  <Phone className="w-4 h-4" />
                  <a
                    href={`tel:${resource.phone}`}
                    onClick={() => recordResourceClick(`${resource.name} - phone`)}
                    className="hover:underline"
                  >
                    {resource.phone}
                  </a>
                </div>
              )}
              {resource.website && (
                <div className="flex items-center gap-2 text-gray-800">
                  <ExternalLink className="w-4 h-4" />
                  <a
                    href={`https://${resource.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => recordResourceClick(`${resource.name} - website`)}
                    className="hover:underline"
                  >
                    Visit Website
                  </a>
                </div>
              )}
              {resource.address && (
                <div className="flex items-start gap-2 text-gray-700">
                  <MapPin className="w-4 h-4 mt-1" />
                  <span className="text-sm">{resource.address}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* National Resources */}
      <div className="mt-12 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="text-xl font-semibold text-gray-900 mb-3">
          National Resources
        </h3>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-gray-800">
            <Phone className="w-4 h-4" />
            <span className="font-medium">National Domestic Violence Hotline:</span>
            <a
              href="tel:1-800-799-7233"
              onClick={() => recordResourceClick('National Domestic Violence Hotline - phone')}
              className="hover:underline"
            >
              1-800-799-7233
            </a>
          </div>
          <p className="text-sm text-gray-600 ml-6">Available 24/7 in over 200 languages</p>
        </div>
      </div>
    </div>
  );
}