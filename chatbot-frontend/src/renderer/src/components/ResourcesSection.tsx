import { ExternalLink, MapPin, Phone } from 'lucide-react';

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
  return (
    <div className="max-w-5xl mx-auto">
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
                  <a href={`tel:${resource.phone}`} className="hover:underline">
                    {resource.phone}
                  </a>
                </div>
              )}
              
              {resource.website && (
                <div className="flex items-center gap-2 text-gray-800">
                  <ExternalLink className="w-4 h-4" />
                  <a 
                    href={resource.website}
                    target="_blank"
                    rel="noopener noreferrer"
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
      
      <div className="mt-12 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="text-xl font-semibold text-gray-900 mb-3">
          National Resources
        </h3>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-gray-800">
            <Phone className="w-4 h-4" />
            <span className="font-medium">National Domestic Violence Hotline:</span>
            <a href="tel:1-800-799-7233" className="hover:underline">
              1-800-799-7233
            </a>
          </div>
          <p className="text-sm text-gray-600 ml-6">Available 24/7 in over 200 languages</p>
        </div>
      </div>
    </div>
  );
}